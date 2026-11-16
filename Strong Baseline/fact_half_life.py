"""Pooled fact retention and empirical half-life for the first 12 articles.

Usage:
    python fact_half_life.py news_2019-07.json pilot_judgments_t10_llama_v1.xlsx
"""
import json
import sys
from collections import Counter
from pathlib import Path

import pandas as pd

model_name = 'chat_v1'

json_path = Path(sys.argv[1]) if len(sys.argv) > 1 else Path('../data/news_2019-07.json')
excel_path = Path(sys.argv[2]) if len(sys.argv) > 2 else Path(f'pilot_judgements_t10_{model_name}.xlsx')

with open(json_path, encoding='utf-8') as f:
    articles = json.load(f)[:12]

# Original fact IDs and their types form the denominator for every iteration.
fact_types = {
    (article['article_id'], fact['fact_id']): fact['type']
    for article in articles
    for fact in article['atomic_facts']
}
totals = Counter(fact_types.values())

judgments = pd.read_excel(excel_path, sheet_name='Fact Judgments')
judgments = judgments[judgments['article_id'].isin({a['article_id'] for a in articles})]

rows = []
for branch in ('A', 'B'):
    for generation in range(1, 11):
        # Both branches use the same summary at T1.
        step = judgments[
            (judgments['generation'] == generation)
            & (judgments['branch'] == ('shared' if generation == 1 else branch))
        ]
        labels = {}
        for record in step.itertuples(index=False):
            key = (record.article_id, record.fact_id)
            if key in fact_types:
                if key in labels:
                    raise ValueError(f'Duplicate judgment: {key}, {branch}, T{generation}')
                labels[key] = str(record.claude_label).strip().lower()

        missing = set(fact_types) - set(labels)
        if missing:
            raise ValueError(
                f'Missing {len(missing)} fact judgments for branch {branch}, T{generation}; '
                f'example: {next(iter(missing))}'
            )

        present = Counter(fact_types[key] for key, label in labels.items() if label == 'present')
        for fact_type in sorted(totals):
            rows.append({
                'branch': branch,
                'generation': generation,
                'fact_type': fact_type,
                'original_facts': totals[fact_type],
                'present_facts': present[fact_type],
                'retention_pct': round(100 * present[fact_type] / totals[fact_type], 2),
            })

retention = pd.DataFrame(rows)
half_lives = []
for (branch, fact_type), group in retention.groupby(['branch', 'fact_type'], sort=True):
    crossed = group.loc[group['retention_pct'] <= 50, 'generation']
    half_lives.append({
        'branch': branch,
        'fact_type': fact_type,
        'half_life': f'T{int(crossed.iloc[0])}' if not crossed.empty else '>T10',
    })

half_lives = pd.DataFrame(half_lives)
retention.to_csv(f'retention_by_iteration_{model_name}.csv', index=False)
half_lives.to_csv(f'fact_half_lives_{model_name}.csv', index=False)

print('\nPooled half-lives across the first 12 articles:')
print(half_lives.pivot(index='fact_type', columns='branch', values='half_life').to_string())
print(f'\nSaved retention_by_iteration.csv and fact_half_lives_{model_name}.csv')
