// Define the server.
const server = "http://localhost:8080";
const highlight_endpoint = server + "/convert_passage";
const linkbox_endpoint = server + "/get_links";
var linkbox_visible = false;
var active_sentence = '';

main().catch(); //when I run the main method to replace text, it prevents overlays. I wonder why. maybe I have separated innerHTML and the dom? The dom is no longer the html that's being rendered...
// long term I need an indexing scheme for the text.

async function fetchData(endpoint, data) {
    var url = endpoint + "?"
    for (key in data) {
        url += key + "=" + data[key] + "&"
    }
    let response = await fetch(url);
    let text = await response.text();
    return text;
  }

async function fetchJson(endpoint, data) {
    var url = endpoint + "?"
    for (key in data) {
        url += key + "=" + data[key] + "&"
    }
    let response = await fetch(url);
    let res = await response.json();
    return res;
}

  async function postData(endpoint, data) {
    const response = await fetch(endpoint, {
        method: 'POST',
        body: JSON.stringify(data),
        mode: 'cors',
        headers: {
            'Accept': 'application/json',
            'Content-Type': 'application/json',
        }
    });
    const text = await response.text();
    return text;
};

function replace(oldNode, newNode) {
    oldNode.parentNode.replaceChild(newNode, oldNode);
}

async function main(){
    console.log("NEWSREADER initializing...");
    console.log(document.body);

    const container = document.createElement('div');
    container.classList.add('extension-content');
    container.id = "extension-content";
    document.body.appendChild(container);

    const paragraphs = getText(document.body);
    for (var i = 0; i < paragraphs.length; i++) {
        var new_paragraph = paragraphs[i].cloneNode(false); // clone the node but not the children
        var text = paragraphs[i].textContent;
        var data = {
            'paragraph': text,
            'url': window.location.href,
        }
        new_html = await fetchData(highlight_endpoint, data);
        console.log(new_html)
        new_paragraph.innerHTML = new_html;
        replace(paragraphs[i], new_paragraph);
    }

    const highlightSpans = document.getElementsByClassName('highlight');
    for (i in highlightSpans) {
        highlightSpans[i].onclick = handleClick;
    }
}

async function handleClick() {
    var linkbox = document.getElementById('linkbox');
    if (linkbox === null) {
        console.log('CREATING FIRST BOX');

        linkbox = await make_linkbox(this);
        active_sentence = this.textContent;
        display_linkbox(this, linkbox);

    } else if (this.textContent === active_sentence) { // clicked on the active one, so hiding.
        console.log("HIDING BOX");

        linkbox.style.display = 'none';
        linkbox.parentNode.removeChild(linkbox);
        active_sentence = '';

    } else { // click on a different one.
        console.log("REPLACING BOX");
        
        linkbox.parentNode.removeChild(linkbox);
        linkbox = await make_linkbox(this);
        display_linkbox(this, linkbox);
        active_sentence = this.textContent;
    }
}

function display_linkbox(linker, linkbox) {
    console.log(linkbox);

    const scrollX = window.scrollX;
    const scrollY = window.scrollY;

    var container = document.getElementById('extension-content');
    container.appendChild(linkbox);
    linkbox.style.display = 'block';

    const linker_pos = linker.getBoundingClientRect();
    linkbox.style.top = `${linker_pos.top + scrollY - 100}px`;
    linkbox.style.left = `${linker_pos.right + scrollX + 50}px`;

    linkbox.style.display = 'block';
    linkbox_visible = true;
}

async function make_linkbox(highlight_span) {
    const text = highlight_span.textContent;

    const objects = await fetchJson(linkbox_endpoint, {'sentence': text});

    // make the linkbox
    var linkbox = document.createElement('div');
    linkbox.classList.add('link-box');
    linkbox.id = "linkbox";

    for (var i = 0; i < objects.length; i++) {
        obj = objects[i]; 
        if (obj['target'] === window.location.href) {
            console.log("Self-reference");
        } else {
            const linkcard = make_linkcard(obj['title'], obj['text'], obj['target'], obj['relation'])
            linkbox.appendChild(linkcard);
            console.log(linkcard);
        }
    }

    // var container = document.createElement('div');
    // container.classList.add('extension-content');
    // container.appendChild(linkbox);

    return linkbox;
}

function redirect(url) {
    window.location.href = url;
}

function make_linkcard(title, text, target, reltype) {
    var linkcard = document.createElement('div');
    linkcard.classList.add('link-card');
    if (reltype === 'contradiction') {
        linkcard.classList.add('link-card-c');
    }
    if (reltype === 'entailment') {
        linkcard.classList.add('link-card-e');
    }

    var gridTitle = document.createElement('div');
    gridTitle.classList.add('gridTitle');
    var h1 = document.createElement('h1');
    h1.textContent = title;
    gridTitle.appendChild(h1);

    var content = document.createElement('div');
    content.classList.add('link-card-content');
    content.classList.add('gridText');
    var p = document.createElement('p');
    p.textContent = text;
    content.appendChild(p);
    //TODO: USE THE FANCY JS CODE TO TRUNCATE

    var gridImg = document.createElement('div');
    gridImg.classList.add('gridImg');
    var favicon = document.createElement('img');
    favicon.src = chrome.runtime.getURL('images/' + title);
    favicon.alt = "Favicon for " + title;
    gridImg.appendChild(favicon);
    
    var gridcontainer = document.createElement('div');
    gridcontainer.classList.add('gridContainer');

    gridcontainer.appendChild(gridImg);
    gridcontainer.appendChild(gridTitle);
    gridcontainer.appendChild(content);
    linkcard.appendChild(gridcontainer);
    linkcard.onclick = function () {
        redirect(target);
    };

    return linkcard;
}

function getText(node) {
    // Extracts text, and returns a pointer to the text AND 
    var paragraphs = document.getElementsByTagName("p");
    return paragraphs;
}