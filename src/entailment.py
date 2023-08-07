from transformers import AutoTokenizer, AutoModelForSequenceClassification
from torch.utils.data import Dataset, DataLoader
import torch
import functools
from tqdm import tqdm

nli_model_name = 'roberta-large-mnli'

nli_model = None
nli_tokenizer = None

def init_model(device=None):
    global nli_tokenizer
    nli_tokenizer = AutoTokenizer.from_pretrained(nli_model_name)
    global nli_model
    nli_model = AutoModelForSequenceClassification.from_pretrained(nli_model_name)
    if device is not None:
        nli_model.to(device)
        
class NLIDataset(Dataset):
    def __init__(self, nli_data):
        super().__init__()
        self.data = nli_data
        
    def __getitem__(self, idx):
        return self.data[idx]
    
    def __len__(self):
        return len(self.data)
    
def collate_nli(xs, tokenizer):
    res = []
    for p,h in xs:
        res.append(tokenizer.encode(f"{p}", f"{h}", return_tensors='pt', truncation_strategy='only_first', padding='max_length', max_length=128))
    res = torch.cat(res, dim=0)
    return res

def classify_nli(pairs, device):
    dataset = NLIDataset(pairs)
    collator = functools.partial(collate_nli, tokenizer=nli_tokenizer)
    dataloader = DataLoader(dataset, collate_fn=collator, batch_size=8, shuffle=False)
    logit_results = []
    with torch.no_grad():
        for b in tqdm(dataloader):
            inputs = b
            outputs = nli_model(inputs.to(device))[0].cpu()
            logit_results.append(outputs)
    combined_results = torch.cat(logit_results, dim=0)
    class_probability = torch.nn.Softmax(dim=1)(combined_results)
    return class_probability
