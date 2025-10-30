from llama_index.core.extractors import BaseExtractor

class MetaDataExtractor(BaseExtractor):
    async def aextract(self, nodes):
        metadata_list = []

        for node in nodes:
            filename = node.metadata.get("file_name", "").strip()
            # remove file extensions
            filename = filename.replace(".docx", "").replace(".pdf", "")
            parts = filename.split()

            # file attribute
            year = None
            source = "Unknown"
            article_id = None
            title = filename

            # Check if it followed the standard of ([year/month/date] [p2]) etc...
            if parts and parts[0].isdigit() and len(parts[0]) == 8:
                year = int(parts[0][:4])

                # Find article id
                id_index = next((i for i, p in enumerate(parts[2:], start=2) if p.isdigit()), None)

                if id_index is not None:
                    source = " ".join(parts[2:id_index])
                    article_id = parts[id_index]
                    title = " ".join(parts[id_index + 1:]).capitalize()
                else:
                    source = parts[2] if len(parts) > 2 else "Unknown"

            else:
                title = filename.capitalize()

            metadata_list.append({
                "filename": filename,
                "year": year,
                "source": source,
                "article_id": article_id,
                "title": title
            })

        return metadata_list

