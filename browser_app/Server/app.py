import flask
from flask import Flask, request
from nltk.tokenize import sent_tokenize
from pathlib import Path
import json
import re

app = Flask(__name__)

database_path = (Path(__file__) / '../../Data').resolve()
url_pattern = r'(?:https?:\/\/)?(\S+?)\/'

def load_database(path):
    db = {}
    for f in path.glob('*.json'):
        with open(f) as fp:
            data = json.load(fp)
            for article in data:
                for sent in article['supports']:
                    claim = sent['my_claim']
                    targets = []
                    for l in sent['links']:
                        l['label'] = "entailment"
                        targets.append(l)
                    if claim in db:
                        db[claim].extend(targets)
                    else:
                        db[claim] = targets
                        
                for sent in article['contradicts']:
                    claim = sent['my_claim']
                    targets = []
                    for l in sent['links']:
                        l['label'] = "contradiction"
                        targets.append(l)
                    if claim in db:
                        db[claim].extend(targets)
                    else:
                        db[claim] = targets

    return db

@app.route('/', methods=['OPTIONS'])
def handle_preflight():
    resp = flask.Response("got preflight")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With"
    return resp

@app.route('/get_links', methods=['POST', 'GET'])
def handle_post_get_links():
    sentence = request.args['sentence']

    result = []
    if sentence in database:
        targets = database[sentence]
        for t in targets:
            for source in t['source']:
                matches = re.findall(url_pattern, source)
                print(matches)
                obj = {
                    'title': matches[0],
                    'text': t['their_claim'],
                    'target': source,
                    'relation': t['label'],
                }
                result.append(obj)

    print(result)
    resp = flask.Response(json.dumps(result), status=200, mimetype="application/json")
    resp.headers["Access-Control-Allow-Origin"] = '*'
    resp.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With"
    return resp
    

@app.route('/convert_passage', methods=['POST', 'GET'])
def handle_post_convert_passage():
    print(request.args)
    paragraph = request.args['paragraph']
    url = request.args['url']

    sentences = sent_tokenize(paragraph)
    inner_html = []
    for s in sentences:
        if s in database:
            targets = database[s]
            n_contr = len([t for t in targets if t['label'] == 'contradiction'])
            n_supp = len([t for t in targets if t['label'] == 'entailment'])
            if n_contr > n_supp:
                inner_html.append(f'<span class="highlight highlight-c">{s}</span>')
            elif n_supp > n_contr:
                inner_html.append(f'<span class="highlight highlight-e">{s}</span>')
            else:
                inner_html.append(f'<span class="highlight">{s}</span>')
        else:
            inner_html.append(s)
    inner_html = ' '.join(inner_html)

    resp = flask.Response(inner_html, status=200, mimetype="application/json")
    resp.headers['Access-Control-Allow-Origin'] = '*'
    resp.headers["Access-Control-Allow-Methods"] = "GET, PUT, POST, OPTIONS"
    resp.headers["Access-Control-Allow-Headers"] = "Cache-Control, Pragma, Origin, Authorization, Content-Type, X-Requested-With"
    return resp


if __name__ == "__main__":
    database = load_database(database_path)
    app.run(debug=True, port=8080)

