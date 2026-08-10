from weaviate.classes.query import HybridFusion, Filter

def retrieve(vectorstore, query, k=5, selected_files=None):
    search_kwargs = {
        "alpha": 0.5,
        "fusion_type": HybridFusion.RELATIVE_SCORE
    }
    
    if selected_files:
        # Construct filter: source LIKE *filename1 OR source LIKE *filename2 ...
        # Note: Weaviate Like support depends on tokenization. 'source' is usually 'pydantic_text' or similar. 
        # Safest for 'source' paths is usually Contains or Like with wildcards if supported.
        # Assuming v4 client filter syntax:
        
        file_filters = [Filter.by_property("source").like(f"*{f}") for f in selected_files]
        if len(file_filters) > 1:
            combined_filter = Filter.any_of(file_filters)
        else:
            combined_filter = file_filters[0]
            
        search_kwargs["filters"] = combined_filter

    return vectorstore.similarity_search(
        query,
        k=k,
        **search_kwargs
    )
