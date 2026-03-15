import sys
from qfluentwidgets import QConfig, ConfigItem, BoolValidator, OptionsConfigItem, OptionsValidator, RangeConfigItem, RangeValidator, Theme, qconfig, FolderListValidator
from pathlib import Path

def isWin11():
    return sys.platform == 'win32' and sys.getwindowsversion().build >= 22000

class Config(QConfig):
    """ Config of the application """
    micaEnabled = ConfigItem("MainWindow", "MicaEnabled", isWin11(), BoolValidator())
    dpiScale = OptionsConfigItem(
        "MainWindow", "DpiScale", "Auto", OptionsValidator([1, 1.25, 1.5, 1.75, 2, "Auto"]), restart=True)
    dataFolders = ConfigItem(
        "Folders", "Data", [], FolderListValidator())

    # Material
    blurRadius  = RangeConfigItem("Material", "AcrylicBlurRadius", 15, RangeValidator(0, 40))

    # LLM Settings
    temperature = OptionsConfigItem("LLM", "Temperature", 0.1, OptionsValidator([0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9]), restart=True)
    max_new_tokens = RangeConfigItem("LLM", "MaxNewTokens", 1024, RangeValidator(128,8129))
    verbose = ConfigItem("LLM", "Verbose", False, BoolValidator())

    # Reranker Settings
    top_n = RangeConfigItem("Retrieval", "TopN", 5, RangeValidator(1,1000))

    # QueryEngine Settings
    similarity_top_k = RangeConfigItem("Retrieval", "SimilarityTopK", 25, RangeValidator(1,1000))
    citation_chunk_size = RangeConfigItem("Retrieval", "CitationChunkSize", 512, RangeValidator(128, 2048))

YEAR = 2025
AUTHOR = "Ethan Yin"

cfg = Config()
cfg.themeMode.value = Theme.AUTO

# Default path
config_file_path = Path("app/config/config.json")

# Check to see if config folder exist
config_file_path.parent.mkdir(parents=True, exist_ok=True)

# load config
qconfig.load(config_file_path, cfg)

# If one doesn't exist then generate one 
if not config_file_path.exists():
    qconfig.save()
    print("Generate new config.json file with default settings.")