"""
Data models for the AI Report Quality Judge.

This module defines the structured data models used throughout the application,
including input/output schemas and internal data structures.
"""
from pydantic import BaseModel, Field, validator
from typing import Dict, List, Optional, Union
from datetime import datetime


class ReportEvaluationResult(BaseModel):
    """
    Standard output format for report quality evaluation results.
    """
    score: int = Field(..., ge=1, le=100, description="Quality score from 1-100")
    reasoning: str = Field(..., description="Detailed explanation for the score")
    metadata: Dict = Field(default_factory=dict, description="Additional metadata about the evaluation")
    
    @validator('score')
    def check_score_range(cls, v):
        """Validate score is within allowed range"""
        if v < 0 or v > 100:
            # Return 0 for invalid scores (parser errors)
            return 0
        return v


class ReportEvaluationRequest(BaseModel):
    """
    Standard input format for requesting a report evaluation.
    """
    report_content: str = Field(..., description="The full text content of the report to evaluate")
    model_key: str = Field("gpt-o1-mini", description="The model to use for evaluation")
    temperature: float = Field(0.3, ge=0.0, le=1.0, description="Temperature for LLM generation")


class EvaluationBatchResult(BaseModel):
    """
    Container for a batch of evaluation results, e.g., when processing multiple reports.
    """
    results: List[Dict[str, Union[ReportEvaluationResult, str]]] = Field(
        ..., description="List of evaluation results or error messages"
    )
    timestamp: datetime = Field(default_factory=datetime.now, description="When the batch evaluation was performed")
    summary: Optional[Dict] = Field(None, description="Optional summary statistics for the batch")
    
    def add_result(self, file_path: str, result: Union[ReportEvaluationResult, Exception]):
        """
        Add a result to the batch.
        
        Args:
            file_path: Path to the evaluated file
            result: Either an evaluation result or an exception if processing failed
        """
        if isinstance(result, Exception):
            self.results.append({
                "file_path": file_path,
                "status": "error",
                "error": str(result)
            })
        else:
            self.results.append({
                "file_path": file_path,
                "status": "success",
                "result": result
            })
    
    def get_successful_results(self) -> List[Dict]:
        """
        Return only the successful evaluations from the batch.
        
        Returns:
            List of dictionaries containing successful evaluation results
        """
        return [r for r in self.results if r.get("status") == "success"]
    
    def get_failed_results(self) -> List[Dict]:
        """
        Return only the failed evaluations from the batch.
        
        Returns:
            List of dictionaries containing error information
        """
        return [r for r in self.results if r.get("status") == "error"]
    
    def compute_summary(self) -> Dict:
        """
        Compute summary statistics for the batch.
        
        Returns:
            Dictionary with summary statistics
        """
        successful = self.get_successful_results()
        failed = self.get_failed_results()
        
        if not successful and not failed:
            return {"status": "empty", "message": "No results to summarize"}
        
        # Gather statistics
        scores = [r["result"].score for r in successful]
        
        summary = {
            "total_files": len(self.results),
            "successful": len(successful),
            "failed": len(failed),
            "success_rate": len(successful) / len(self.results) if self.results else 0,
        }
        
        # Add score statistics if we have any successful evaluations
        if scores:
            summary.update({
                "avg_score": sum(scores) / len(scores),
                "min_score": min(scores),
                "max_score": max(scores),
            })
        
        self.summary = summary
        return summary 