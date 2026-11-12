# data/ — Fact Half-Life (CIS 5300)

## Files

| File | Contents |
| --- | --- |
| `news_2019-07.json` | 100 BBC News passages from July 2019, each with its gold atomic facts (2,275 facts in total) |

Encoding: UTF-8. Format: one JSON array of article objects.

## Source and selection

- Source: [`RealTimeData/bbc_news_alltime`](https://huggingface.co/datasets/RealTimeData/bbc_news_alltime), subset `2019-07` (1,366 articles).
- **Sport removed.** Any article whose section contains "Sport", or whose URL contains `/sport/`, was dropped.
- **Cleaned.** HTML entities and tags, image captions, sub-headings (paragraphs that don't end like a sentence) and social-media embed and cookie boilerplate ("This Twitter post cannot be displayed…", "Allow … content?") were removed.
- **Deduplicated** on headline and on the opening text.
- **Length filter.** Articles under 490 words after cleaning were skipped.
- **Sampling.** The remaining articles were shuffled with seed 42, and the first 100 that passed every filter were kept as `NEWS_001` … `NEWS_100`.
- **Truncation.** `true_text` is cut at the sentence end closest to 500 words. The result is 474–518 words, with a mean of 499.7.

## Schema

### Article object

| Field | Type | Description |
| --- | --- | --- |
| `article_id` | string | Stable ID, `NEWS_001` … `NEWS_100` |
| `title` | string | BBC headline, with the " - BBC News" suffix removed |
| `section` | string or null | BBC section |
| `published` | string | Publication date, `YYYY-MM-DD` |
| `source_url` | string | Original BBC article URL |
| `word_count` | int | Number of words in `true_text` |
| `true_text` | string | The passage T0: the truncated, cleaned article and the input to the summarization chain |
| `hf_dataset` | string | `RealTimeData/bbc_news_alltime` |
| `hf_subset` | string | `2019-07` |
| `num_facts` | int | Number of entries in `atomic_facts` |
| `atomic_facts` | array | Gold atomic facts (see the next table) |

### Atomic fact object

| Field | Type | Description |
| --- | --- | --- |
| `fact_id` | string | `<article_id>_F<nn>`, e.g. `NEWS_007_F03` |
| `fact` | string | Short, stand-alone claim that is true or false on its own |
| `source_span` | string | Verbatim substring of `true_text` that supports the fact |
| `type` | string | One of `named_entity`, `numerical`, `temporal`, `spatial`, `event`, `relation`, `causal`, `verbal` |
| `key_value` | string | The core value or entity to check (number, date, name, place) |
| `negation` | bool | The fact contains a negation |
| `uncertainty` | bool | The fact is hedged ("may", "is expected to") |
| `quotation` | bool | The fact is a direct quote or reported speech |
| `attribution` | string or null | Who stated the fact; null if it is the narrator's |
| `opinion` | bool | The fact is a subjective opinion |
| `salience` | string | `core` or `peripheral` |

## Stats

- 100 articles and 2,275 facts, with 19–25 facts per article.
- Facts by type: verbal 520, event 459, numerical 375, named_entity 310, temporal 237, causal 151, spatial 124, relation 99.
- Salience: 1,024 core and 1,251 peripheral.

## Notes

- The facts still need to be checked by hand by team members.
- Every `source_span` has been checked by script to be an exact substring of its article's `true_text`.
