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
            if parts[0].isdigit() and len(parts[0]) == 8:

                # Get year
                year = ""
                count = 0
                for char in parts[0]:
                    if count >= 4:
                        break
                    year += char
                    count += 1
                # type cast to int
                year = int(year)

                # Check for article id
                id_index = None
                for i in range(2, len(parts)):
                    if parts[i].isdigit():
                        id_index = i
                        break

                if id_index is not None:
                    source = " "
                    for i in range(2, id_index):
                        # Add each word before the article id
                        source += parts[i]
                        source += " "

                    # Get article ID
                    article_id = parts[id_index]

                    # Get title
                    title = " "
                    for i in range(id_index + 1, len(parts)):
                        title += parts[i]
                        title += " "

            # If it doesn't follow the naming convention
            # then we'll use the entire length as a name
            else:
                title = filename

            metadata_list.append({
                "year": year,
                "source": source,
                "article_id": article_id,
                "title": title
            })

        return metadata_list