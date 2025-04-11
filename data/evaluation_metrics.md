# Evaluation Metrics for AI Report Quality Judge

This document defines the quantitative metrics used to evaluate the performance of the AI Report Quality Judge against human evaluations.

## Primary Metrics

### 1. Score Correlation

**Pearson Correlation Coefficient (r)**  
Measures the linear correlation between AI-assigned scores and human-assigned scores.
- Perfect positive correlation: r = 1
- No correlation: r = 0
- Perfect negative correlation: r = -1

**Interpretation:**
- r ≥ 0.8: Excellent correlation
- 0.6 ≤ r < 0.8: Strong correlation
- 0.4 ≤ r < 0.6: Moderate correlation
- 0.2 ≤ r < 0.4: Weak correlation
- r < 0.2: Very weak or no correlation

**Spearman's Rank Correlation Coefficient (ρ)**  
Measures the monotonic relationship between AI and human rankings of reports.
- This is useful to determine if the AI ranks reports in the same order as humans, even if the absolute scores differ.

### 2. Score Difference Metrics

**Mean Absolute Error (MAE)**  
Average absolute difference between AI and human scores.
```
MAE = (1/n) * Σ|AI_score - human_score|
```

**Root Mean Square Error (RMSE)**  
Square root of the average of squared differences between AI and human scores.
```
RMSE = sqrt((1/n) * Σ(AI_score - human_score)²)
```
- RMSE gives higher weight to larger errors compared to MAE.

**Score Difference Distribution**  
- Percentage of reports where |AI_score - human_score| ≤ 5 points
- Percentage of reports where |AI_score - human_score| ≤ 10 points
- Percentage of reports where |AI_score - human_score| ≤ 15 points

### 3. Category-Level Agreement

For each evaluation category (structure, analysis, evidence, reasoning, clarity):
- Calculate correlation coefficients (Pearson and Spearman) between AI and human scores
- Calculate MAE and RMSE for category-specific scores

### 4. Reasoning Quality Metrics

**Reasoning Similarity Score**  
Using an embedding model to calculate semantic similarity between AI reasoning and human reasoning.
```
similarity = cosine_similarity(embedding(AI_reasoning), embedding(human_reasoning))
```

**Key Points Coverage**  
Percentage of key points identified by human evaluators that are also mentioned in the AI reasoning.

**False Insights Rate**  
Number of incorrect or unsupported insights in AI reasoning per report, as identified by human reviewers.

## Secondary Metrics

### 1. Consistency Metrics

**Standard Deviation of Error**  
Measures how consistent the AI's scoring is across different types of reports.

**Intraclass Correlation Coefficient (ICC)**  
Measures the reliability of AI ratings compared to human ratings.

### 2. Bias Metrics

**Length Bias**  
Correlation between report length and score difference (AI - human).

**Topic Bias**  
Variation in scoring accuracy across different report topics or domains.

### 3. Performance Metrics

**Processing Time**  
Average time taken to evaluate a report.

**Resource Usage**  
Memory and computational resources required for evaluation.

## Success Criteria

The AI Report Quality Judge will be considered successful if it meets the following criteria:

1. Pearson correlation coefficient (r) ≥ 0.7 for overall scores
2. Mean Absolute Error (MAE) ≤ 10 points
3. At least 80% of reports with |AI_score - human_score| ≤ 15 points
4. Reasoning similarity score ≥ 0.7
5. Key points coverage ≥ 70%

These metrics will be used to evaluate the performance of different versions of the AI Report Quality Judge and guide further improvements. 