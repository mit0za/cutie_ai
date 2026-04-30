from llama_index.core.vector_stores.types import MetadataInfo, VectorStoreInfo

# This acts as a manual for the Auto Retrieverr.
# It tells the LLM what filters are available in our db
vector_store_info = VectorStoreInfo(
    content_info="Articles and documents from a historical newspaper archieve",
    
    #Defines columns the LLM is allowed to filter by
    metadata_info=[
        MetadataInfo(
            name="year",
            type="integer",
            description="The year the article was published",
        ),
        MetadataInfo(
            name="source",
            type="string",
            description="The name of the newspaper or publication source",
        )
    ]
)