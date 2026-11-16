import argparse
from pathlib import Path
import pandas as pd


def run(input_path: Path, output_dir: Path):
    facts = pd.read_excel(input_path, sheet_name="Fact Judgments")
    summaries = pd.read_excel(input_path, sheet_name="Summaries")
    required_facts = {"summary_key", "article_id", "branch", "generation", "fact_id", "type", "claude_label"}
    required_summaries = {"summary_key", "summarizer_model"}
    for name, df, required in (("Fact Judgments", facts, required_facts), ("Summaries", summaries, required_summaries)):
        missing = required - set(df.columns)
        if missing:
            raise ValueError(f"Missing columns in {name}: {sorted(missing)}")

    # Restrict to final-generation judgments from both independent branches.
    facts = facts.loc[facts["generation"].eq(10) & facts["branch"].isin(["A", "B"])].copy()
    facts["claude_label"] = facts["claude_label"].astype(str).str.strip().str.lower()
    facts["type"] = facts["type"].astype(str).str.strip().str.lower()
    allowed = {"present", "absent", "mutated"}
    invalid = set(facts["claude_label"].unique()) - allowed
    if invalid:
        raise ValueError(f"Unexpected judge labels: {sorted(invalid)}")
    if facts.empty:
        raise ValueError("No T10 fact judgments for Branch A/B")

    model_lookup = summaries[["summary_key", "summarizer_model"]].drop_duplicates()
    if model_lookup["summary_key"].duplicated().any():
        raise ValueError("Conflicting summarizer models for a summary_key")
    facts = facts.merge(model_lookup, on="summary_key", how="left", validate="many_to_one")
    if facts["summarizer_model"].isna().any():
        raise ValueError("Missing summarizer model for some judgments")
    facts = facts.rename(columns={"summarizer_model": "model", "type": "category"})

    # One judge classification per original fact, article, model and branch.
    unique_key = ["article_id", "model", "branch", "fact_id"]
    if facts.duplicated(unique_key).any():
        raise ValueError("Duplicate T10 fact judgments detected; inspect input before calculating retention")
    facts["retained"] = facts["claude_label"].eq("present").astype(int)
    facts["mutated"] = facts["claude_label"].eq("mutated").astype(int)

    output_dir.mkdir(parents=True, exist_ok=True)
    def aggregate(group_cols):
        result = (facts.groupby(group_cols, dropna=False)
                  .agg(total_original_facts=("fact_id", "nunique"),
                       present_facts=("retained", "sum"),
                       mutated_facts=("mutated", "sum"))
                  .reset_index())
        result["absent_facts"] = result["total_original_facts"] - result["present_facts"] - result["mutated_facts"]
        result["retention_pct"] = (100 * result["present_facts"] / result["total_original_facts"]).round(2)
        return result.sort_values(group_cols).reset_index(drop=True)

    article = aggregate(["article_id", "model", "branch", "category"])
    overall = aggregate(["model", "branch", "category"])
    all_categories = aggregate(["model", "branch"])

    article.to_csv(output_dir / "retention_by_article_category.csv", index=False)
    overall.to_csv(output_dir / "retention_by_model_branch_category.csv", index=False)
    all_categories.to_csv(output_dir / "retention_overall_by_model_branch.csv", index=False)

    comparison = overall.pivot(index=["model", "category"], columns="branch", values="retention_pct")
    comparison = comparison.rename(columns={"A": "branch_A_pct", "B": "branch_B_pct"}).reset_index()
    if {"branch_A_pct", "branch_B_pct"}.issubset(comparison.columns):
        comparison["B_minus_A_percentage_points"] = (comparison["branch_B_pct"] - comparison["branch_A_pct"]).round(2)
    comparison.to_csv(output_dir / "branch_comparison.csv", index=False)

    print(f"Articles: {facts['article_id'].nunique()} | Models: {', '.join(sorted(facts['model'].unique()))}")
    print(f"T10 judgments: {len(facts)}")
    print("\nFinal retention by category (micro-averaged across articles):")
    print(overall.to_string(index=False))
    print("\nOverall retention across all categories:")
    print(all_categories.to_string(index=False))
    print(f"\nSaved four CSV files in {output_dir.resolve()}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--input", type=Path, default=Path("pilot_judgments_t10_claude_v1.xlsx"))
    parser.add_argument("--output-dir", type=Path, default=Path("baseline_results"))
    args = parser.parse_args()
    run(args.input, args.output_dir)
