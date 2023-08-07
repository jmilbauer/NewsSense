import openai
import json
import copy

openai.api_key = ""
model_name = 'text-davinci-003'

segmentation_template = """Extract all the claims from a sentence, ignoring extraneous words such as unimportant adverbs. A sentence may contain multiple claims. Each claim should be of the form <subject> <predicate> <object>. Replace all pronouns with their antecedents, resolving any reference uncertainty.

Sentence: "The 3rd and 4th stations all announced that they would be postponed, and the Monaco station was subsequently cancelled."
Claim: Monaco station was cancelled.
Claim: 4th station announced the 4th station would be postponed.
Claim: The 3rd stations announced the 3rd station would be postponed.
Claim: The 4th stations postponed.
Claim: The 3rd stations postponed.

Sentence: "Lewis Hamilton and Mercedes have once again confirmed themselves as drivers and constructors world champions."
Claim: Mercedes confirmed themselves as constructors world champions.
Claim: Lewis Hamilton confirmed themselves as drivers world champions.

Sentence: "Local organizers in East Palestine, Ohio on Monday said their activism has successfully pressured rail company Norfolk Southern to agree to a limited relocation plan for some residents affected by last month's train derailment, but added they have no intention of backing down from their demand for justice for thousands of people in the area who are struggling in the aftermath of the accident."
Claim: Local organizers said their activism has pressured rail company Norfolk Southern to agree to a limited relocation plan.
Claim: Local organizers have no intention of backing down from the local organizers' demand for justice.
Claim: Rail company Norfolk Southern agree to a limited relocation plan.

Sentence: """

def make_prompt(sentence, template=segmentation_template):
    return f"{template} {sentence}"

def get_claims(sentence):
    prompt = make_prompt(' '.join(sentence.split())),
    completion = openai.Completion.create(
        model=model_name,
        prompt=prompt,
        max_tokens=128,
        temperature=0,
    )
    claims = completion.choices[0].text.strip().split('\n')
    claims = [c for c in claims if c[:6] == 'Claim:']
    claims = [c[6:].strip() for c in claims]
    return completion, claims


def merge_paragraphs(paragraphs, min_words, max_words):
    ps = copy.deepcopy(paragraphs)
    
    while True:
        lens = [len(p.split()) for p in ps]
        merges = [(x+y, i) for i, (x,y) in enumerate(zip(lens, lens[1:])) if x < min_words or y < min_words]
        valid_merges = [(len_, pos_) for len_, pos_ in merges if len_ < max_words]
        if len(valid_merges) == 0:
               break
        _, best_merge = list(sorted(valid_merges))[0]
        
        joined = ' '.join([ps[best_merge], ps[best_merge + 1]])
        ps = ps[:best_merge] + [joined] + ps[best_merge+2:]
        
    return ps
