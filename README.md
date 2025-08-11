We will develop using `llama2:7b`. I recommend you get it from [ollama](https://ollama.com/library/llama2:7b).<br>
We are also using [nomic-embed-text:latest](https://ollama.com/library/nomic-embed-text).<br>
I highly set up a virtual python enviroment because we are in a development phrase which mean<br>
we will build fast and break fast.
# Dependencies
```
pip install -r requirements.txt
```

# Note
The ai model can extract text from word documents and store it in a vector database. I have tested it by putting "18410521 p3 Southern Australian 71614658 NZ separate colony from NSW.docx" from file name 1854 into data/ directory.<br>

I asked **"What was her majesty please about?"**<br>

Ai responsed **Her Majesty was pleased to erect the Islands of New Zealand into a distinct and separate colony."** Which is 100% correct based on the document I gave it.

