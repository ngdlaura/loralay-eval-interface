import datetime
import json 

import streamlit as st
from st_click_detector import click_detector
from annotated_text import annotated_text

import nltk
from nltk.tokenize import sent_tokenize
from nltk.corpus import stopwords

from difflib import SequenceMatcher

try:
    nltk.data.find('tokenizers/punkt')
except LookupError:
    nltk.download('punkt')
try:
    nltk.data.find('corpora/stopwords')
except LookupError:
    nltk.download('stopwords')

all_stopwords = set(stopwords.words('english'))

def highlight_in_gold_sample(sent, gold_summary):
    words_in_sent = sent.lower().split()
    gold_words = gold_summary.split()
    annotated_gold_summ = []
    for w in gold_words:
        if w.lower() not in all_stopwords:
            if w.lower() in words_in_sent:
                annotated_gold_summ.append((w + " ", ""))
            else:
                is_matched = False 
                for w_sent in words_in_sent:
                    if SequenceMatcher(a=w.lower(), b=w_sent).ratio() > 0.8:
                        is_matched = True 
                if is_matched:
                    annotated_gold_summ.append((w + " ", ""))
                else:
                    annotated_gold_summ.append(w + " ")    
        else:
            annotated_gold_summ.append(w + " ") 
    return annotated_gold_summ


def create_sliders(model_name, doc_id):
    def update_slider_coh():
        with open(f"./slider_outputs/{model_name}_{doc_id}_coh", 'a') as fw:
            fw.write(str(st.session_state[f'{model_name}_{doc_id}_coh']) + "\n")

    def update_slider_con():
        with open(f"./slider_outputs/{model_name}_{doc_id}_con", 'a') as fw:
            fw.write(str(st.session_state[f'{model_name}_{doc_id}_con']) + "\n")

    def update_slider_flu():
        with open(f"./slider_outputs/{model_name}_{doc_id}_flu", 'a') as fw:
            fw.write(str(st.session_state[f'{model_name}_{doc_id}_flu']) + "\n")

    def update_slider_rel():
        with open(f"./slider_outputs/{model_name}_{doc_id}_rel", 'a') as fw:
            fw.write(str(st.session_state[f'{model_name}_{doc_id}_rel']) + "\n")

    coherence = st.slider('Coherence', 0., 5., 2.5, 0.1, key=f'{model_name}_{doc_id}_coh', on_change=update_slider_coh)
    consistency = st.slider('Consistency', 0., 5., 2.5, 0.1, key=f'{model_name}_{doc_id}_con', on_change=update_slider_con)
    fluency = st.slider('Fluency', 0., 5., 2.5, 0.1, key=f'{model_name}_{doc_id}_flu', on_change=update_slider_flu)
    relevance = st.slider('Relevance', 0., 5., 2.5, 0.1, key=f'{model_name}_{doc_id}_rel', on_change=update_slider_rel)


def loralay_eval_interface(gold_samples, bigbird_samples, layout_bigbird_samples, doc_id):
    st.title("LoRaLay Evaluation Interface")

    all_doc_ids = tuple([sample_id for sample_id, _ in gold_samples.items()])
    all_doc_ids = sorted(all_doc_ids)
    last_idx = len(all_doc_ids) - 1

    if "doc_idx" not in st.session_state:
        st.session_state.doc_idx = all_doc_ids.index(doc_id)
    else:
        doc_id = all_doc_ids[st.session_state.doc_idx]

    st.header(f"Document {doc_id}")        
        
    placeholder_gold = st.empty()
    placeholder_bigbird, placeholder_layout_bigbird = st.tabs(["BigBird", "BigBird+Layout"])

    with placeholder_gold.container():
        st.subheader("Ground-truth abstract")
        st.write(gold_samples[doc_id])

    bigbird_n_sent = len(bigbird_samples[doc_id])
    layout_bigbird_n_sent = len(layout_bigbird_samples[doc_id])

    def on_change_gen_checkbox(sent_idx, model_name):
        for i in range(bigbird_n_sent):
            if model_name != "bigbird" or i != sent_idx:
                st.session_state[f"chk_bigbird_{doc_id}_{i}"] = False
        for i in range(layout_bigbird_n_sent):
            if model_name != "layout_bigbird" or i != sent_idx:
                st.session_state[f"chk_layout_bigbird_{doc_id}_{i}"] = False

    def on_change_cov_eval(sent_idx, model_name):
        with open(f"./coverage_outputs/{model_name}_{doc_id}_sent{sent_idx}", 'a') as fw:
            fw.write(str(st.session_state[f'cov_{model_name}_{doc_id}_{sent_idx}']) + "\n")


    def display_placeholder_model(model_name, gen_samples, doc_id):
        if model_name == "bigbird":
            st.subheader("Summary generated by BigBird")
        else:
            st.subheader("Summary generated by BigBird+Layout")
        st.info("Summary is split by sentence. Click on any sentence to highlight the corresponding words in the ground-truth abstract.")

        for sent_idx, sent in enumerate(gen_samples[doc_id]):
            left, center, right = st.columns([1, 7, 2])
            with left:
                st.checkbox("", key=f'chk_{model_name}_{doc_id}_{sent_idx}', on_change=on_change_gen_checkbox, args=(sent_idx, model_name))
            with center:
                st.markdown(sent)
            with right:
                st.number_input("Coverage %", 0, 100, 0, 5, key=f'cov_{model_name}_{doc_id}_{sent_idx}', on_change=on_change_cov_eval, args=(sent_idx, model_name))

    with placeholder_bigbird.container():
        display_placeholder_model("bigbird", bigbird_samples, doc_id)
        st.info("Use the sliders below to evaluate the generated summary.")
        create_sliders("bigbird", doc_id)

    for sent_idx in range(bigbird_n_sent):
        if st.session_state[f'chk_bigbird_{doc_id}_{sent_idx}']:
            annotated_gold_summ = highlight_in_gold_sample(
                bigbird_samples[doc_id][sent_idx],
                gold_samples[doc_id] 
            )
            with placeholder_gold.container():
                st.subheader("Abstract")
                annotated_text(*annotated_gold_summ)
    

    with placeholder_layout_bigbird.container():
        display_placeholder_model("layout_bigbird", layout_bigbird_samples, doc_id)
        st.info("Use the sliders below to evaluate the generated summary.")
        create_sliders("layout_bigbird", doc_id)

                
    for sent_idx in range(layout_bigbird_n_sent):
        if st.session_state[f'chk_layout_bigbird_{doc_id}_{sent_idx}']:
            annotated_gold_summ = highlight_in_gold_sample(
                layout_bigbird_samples[doc_id][sent_idx],
                gold_samples[doc_id] 
            )
            with placeholder_gold.container():
                st.subheader("Abstract")
                annotated_text(*annotated_gold_summ)



    def go_to_next():
        st.session_state.doc_idx += 1
    def go_to_previous():
        st.session_state.doc_idx -= 1

    left, _, right = st.columns([1, 8, 1])
    with left:
        if st.session_state.doc_idx > 0:
            st.button('Previous', on_click=go_to_previous)
    with right:
        if st.session_state.doc_idx < last_idx:
            st.button('Next', on_click=go_to_next)
        

def load_samples(samples, is_gold=False):
    samples = [json.loads(sample) for sample in samples]
    samples = {
        sample["id"]: sample["abstract"] if is_gold else sent_tokenize(sample["output"]) for sample in samples
    }
    return samples


if __name__ == "__main__":

    with open("samples/gold.txt") as f:
        gold_samples = f.readlines()
    with open("samples/bigbird-pegasus.txt") as f:
        bigbird_samples = f.readlines()
    with open("samples/layout-bigbird-pegasus.txt") as f:
        layout_bigbird_samples = f.readlines()

    gold_samples = load_samples(gold_samples, is_gold=True)
    bigbird_samples = load_samples(bigbird_samples)
    layout_bigbird_samples = load_samples(layout_bigbird_samples)

    all_doc_ids = tuple([sample_id for sample_id, _ in gold_samples.items()])
    all_doc_ids = sorted(all_doc_ids)

    loralay_eval_interface(gold_samples, bigbird_samples, layout_bigbird_samples, all_doc_ids[0])
