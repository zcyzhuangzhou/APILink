#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/11/20
------------------------------------------
@Modify: 2019/11/20
------------------------------------------
@Description: extract the API mentioned in the SO post from the code.
"""
import gensim
import re
import spacy
from sekg.text.spacy_pipeline.tokenizer import CustomizeSpacy
from bs4 import BeautifulSoup
from sekg.util.code import CodeElementNameUtil
from base import SOPostAPIRecognition
from code_based.baker.ASTParseCodeBasedWithGraphBaker import ASTParseCodeBasedWithGraphBaker
from code_based.baker.ASTParseCodeBasedWithNeo4jBaker import ASTParseCodeBasedWithNeo4jBaker
from code_based.baker.CodeBasedWithGraphBaker import CodeBasedWithGraphBaker
from model.base import SOPost
from script.html_text_preprocessor import HtmlTextPreprocessor


class CodeBasedSOPostAPIRecognition(SOPostAPIRecognition):
    CODE_FRAGMENT_MARK = "-CODE-"
    pattern = re.compile(r'\s+')

    def __init__(self, graph, graph_client):
        self.baker_linker = ASTParseCodeBasedWithGraphBaker(graph=graph, graph_client=graph_client)
        self.name_util = CodeElementNameUtil()
        self.processor = HtmlTextPreprocessor()
        nlp = spacy.load('en_core_web_sm')
        CustomizeSpacy.customize_tokenizer_split_single_lowcase_letter_and_period(nlp)
        CustomizeSpacy.customize_tokenizer_merge_hyphen(nlp)
        CustomizeSpacy.customize_tokenizer_merge_dot_upper_letter(nlp)
        CustomizeSpacy.customize_tokenizer_api_name_recognition(nlp)
        nlp.add_pipe(CustomizeSpacy.customize_sentencizer_merge_colon, before="tagger")
        nlp.add_pipe(CustomizeSpacy.pipeline_merge_bracket, name='pipeline_merge_bracket', after='tagger')
        self.nlp = nlp

    def recognize(self, post: SOPost, is_completed=False):
        """
        return list of APIs
        :param post:
        :return:
        """
        baker_api_qualified_name = []
        body = post.body
        soup = BeautifulSoup(body, "lxml")
        longCodes = soup.find_all(name=["pre", 'blockquote'])

        for tag in longCodes:
            tag.string = " " + self.CODE_FRAGMENT_MARK + " . \n"

        cleanText = soup.get_text()
        decode_clean_text = gensim.utils.decode_htmlentities(cleanText)
        decode_clean_text = re.sub(self.pattern, " ", decode_clean_text.replace('\n', ' ').replace(u'\u00a0', " "))

        doc = self.nlp(decode_clean_text)
        code_sen = []
        doc_sentences = []
        for sen in doc.sents:
            doc_sentences.append(sen.text)
        for index, sen in enumerate(doc_sentences):
            if sen.__contains__("-CODE-") and index == 0:
                code_sen.append(sen)
            elif sen.__contains__("-CODE-") and index != 0:
                code_sen.append(doc_sentences[index - 1][-5:] + ' ' + sen)

        for index, sen in enumerate(code_sen):
            api_qualified_name = {}
            tmp_api_qualified_name = {}
            # code_index = 0
            # for i in range(index):
            #     if code_sen[i] == sen:
            #         code_index = code_index + 1
            code_restore_list = self.processor.code_restore(html=post.body, sentence=sen)
            if not code_restore_list:
                continue
            longCodeText = self.processor.code_restore(html=post.body, sentence=sen)[0]
            tmp_api_qualified_name = self.baker_linker.baker(longCodeText)
            if not tmp_api_qualified_name:
                return baker_api_qualified_name
            for key in tmp_api_qualified_name:
                if key.endswith("]"):
                    api_qualified_name.update({key.rsplit('[', 1)[0]: tmp_api_qualified_name[key]})
                else:
                    api_qualified_name.update({key: tmp_api_qualified_name[key]})
            for key in api_qualified_name:
                flag = False
                processed_sentence = []
                # if index == 0:
                #     processed_sentence = [code_sen[index]]
                # else:
                processed_sentence = [code_sen[index][5:]]
                sentence = [processed_sentence[0].replace("-CODE-", longCodeText)]
                for item in baker_api_qualified_name.copy():
                    if key == item["ori_api"] and api_qualified_name[key] == item["qualified_name"]:
                        item["sentence"].extend(sentence)
                        item["processed_sentence"].extend(processed_sentence)
                        flag = True
                        break
                if not flag:
                    baker_api_qualified_name.append({"ori_api": key,
                                                     "qualified_name": api_qualified_name[key],
                                                     "alias": self.name_util.generate_aliases(api_qualified_name[key]),
                                                     "sentence": sentence,
                                                     "processed_sentence": processed_sentence})
        return baker_api_qualified_name
