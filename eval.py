import json
from llama_index.core.llama_dataset import (
    LabelledRagDataset,
    CreatedBy,
    CreatedByType,
    LabelledRagDataExample,
)

# Load dataset
def load_dataset(json_path):
    with open(json_path, 'r') as file:
        data = json.load(file)

    # Put dataset into order
    dataSet = []
    for item in data:
        example = LabelledRagDataExample(
            query=item["query"],
            query_by=CreatedBy(type=CreatedByType.HUMAN),
            reference_answer=item["reference_answer"],
            reference_contexts=item["reference_contexts"],
            reference_by=CreatedBy(type=CreatedByType.HUMAN)
        )
        dataSet.append(example)

load_dataset("dataset.json")