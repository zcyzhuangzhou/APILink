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
import os
import re
import zipfile
from pathlib import Path
from xml.etree.ElementTree import parse
import gensim
import spacy
from bs4 import BeautifulSoup
from sekg.text.spacy_pipeline.tokenizer import CustomizeSpacy
from sekg.util.code import CodeElementNameUtil
from base import SOPostAPIRecognition
from text_based.linker import TextBasedSOPostAPILinker
from model.base import SOPost


# from spacy.lang.en import English


class TextBasedSOPostAPIRecognition(SOPostAPIRecognition):
    CODE_FRAGMENT_MARK = "-CODE-"
    JAVA_KEY_WORDS = ["abstract", "assert", "boolean", "break", "byte", "case", "catch", "char", "class", "const",
                      "continue", "default", "do", "double", "else", "enum", "extends", "final", "finally", "float",
                      "for", "goto", "if", "implements", "import", "instanceof", "int", "interface", "long", "native",
                      "new", "package", "private", "protected", "public", "return", "strictfp", "short", "static",
                      "super", "switch", "synchronized", "this", "throw", "throws", "transient", "try", "void",
                      "volatile", "while"]
    pattern = re.compile(r'\s+')
    api_patterns = [
        re.compile(r'^(?P<ELE>[a-zA-Z0-9_]*[a-z0-9][A-Z][a-z]+[a-zA-Z0-9_]*)(<.*>)?$'),
        re.compile(r'^(?P<ELE>[a-zA-Z0-9_\.<>]+)\)[a-zA-Z0-9_\,.<>)]*?$'),
        re.compile(r'^(?P<ELE>[a-zA-Z]{2,}(\.[a-zA-Z0-9_]+)+)(<.*>)?$'),
        re.compile(r'^(?P<ELE>((([a-zA-Z0-9_]{2,})(\.))+)([a-zA-Z0-9_]{2,}))?$'),
        re.compile(r'(([a-z_]+([A-Z])[a-z_]+)+)|(([A-Z_]([a-z_]+))+)')
    ]

    def __init__(self):
        self.linker = TextBasedSOPostAPILinker()
        self.name_util = CodeElementNameUtil()
        nlp = spacy.load('en_core_web_sm')
        CustomizeSpacy.customize_tokenizer_split_single_lowcase_letter_and_period(nlp)
        CustomizeSpacy.customize_tokenizer_merge_hyphen(nlp)
        CustomizeSpacy.customize_tokenizer_merge_dot_upper_letter(nlp)
        CustomizeSpacy.customize_tokenizer_api_name_recognition(nlp)
        nlp.add_pipe(CustomizeSpacy.customize_sentencizer_merge_colon, before="tagger")
        nlp.add_pipe(CustomizeSpacy.pipeline_merge_bracket, name='pipeline_merge_bracket', after='tagger')
        self.nlp = nlp
        self.so_tag_list = list(self.__int_tags().keys())

    def __int_tags(self):
        so_path = os.path.dirname(os.path.abspath(__file__))
        tag_path = str(Path(so_path) / "stackoverflow.com-Tags.zip")
        if os.path.exists(tag_path):
            with zipfile.ZipFile(tag_path, 'r') as z:
                f = z.open('Tags.xml')
            doc = parse(f)
            root = doc.getroot()
            tag_data = []
            for child in root:
                tag_data.append(child.attrib)
            tag_dic = {}
            for item in tag_data:
                tag_dic[item["TagName"].lower()] = item
            return tag_dic
        else:
            return {}

    def recognize(self, post: SOPost, is_completed=False):
        """
        return list of APIs
        :param post:
        :param is_completed, whether complete the API into qualified name as much as possible
        :return:
        """
        body = post.body
        title = post.title
        oriApiSet = set()
        soup = BeautifulSoup(body, "lxml")
        longCodeTags = soup.find_all(name=["pre", 'blockquote'])

        for tag in longCodeTags:
            tag.string = " " + self.CODE_FRAGMENT_MARK + " . \n"

        codeTags = soup.find_all(name="code")
        for tag in codeTags:
            # 要使用tag.get_text,因为tag.string可能为空
            if tag.string == " " + self.CODE_FRAGMENT_MARK + " . \n" or not tag.get_text():
                continue
            # 一般类方法不会少于两个字符，少于两个字符可能是一些关键字，或者是自定义标识符
            if len(tag.get_text()) > 2 and tag.get_text() not in self.JAVA_KEY_WORDS:
                if len(tag.get_text().split("(")[0]) < 3:
                    continue
                # 处理code tag文本，不一定是都是api
                oriApiSetFromCodeTag = self.extract_api_from_sentence(tag.get_text())
                oriApiSet.update(oriApiSetFromCodeTag)
        cleanText = soup.get_text()
        decode_clean_text = gensim.utils.decode_htmlentities(cleanText)
        decode_clean_text = re.sub(self.pattern, " ", decode_clean_text.replace('\n', ' ').replace(u'\u00a0', " "))

        # nlp = English()
        # sentencizer = nlp.create_pipe("sentencizer")
        # nlp.add_pipe(sentencizer)
        # nlp = spacy.load("en_core_web_sm", disable=["tagger", "ner", "entity_linker"])

        doc = self.nlp(decode_clean_text)
        for sen in doc.sents:
            api_from_body = self.extract_api_from_sentence(sen.text)
            oriApiSet.update(api_from_body)

        api_from_title = self.extract_api_from_sentence(title, is_title=True)
        oriApiSet.update(api_from_title)
        if is_completed:
            api_qualified_name = []
            # completedApiSet = set()
            api_dic = {}
            for api in oriApiSet:
                if api.__contains__('#'):
                    tmp_api = api.replace('#', '.')
                    completed_api = self.linker.link_one(post, tmp_api)
                else:
                    completed_api = self.linker.link_one(post, api)
                #利用so tag过滤
                if completed_api == api and api.lower() in self.so_tag_list:
                    continue
                # 过滤一些没用的词，例如驼峰式的Java,Android
                if len(completed_api.split(".")) == 1 and len(completed_api.split("(")) == 1:
                    continue
                # completedApiSet.add(completed_api)
                api_dic[api] = completed_api
            soup2 = BeautifulSoup(body, "lxml")
            cleanText2 = soup2.get_text()
            decode_clean_text2 = gensim.utils.decode_htmlentities(cleanText2)
            decode_clean_text2 = re.sub(self.pattern, " ", decode_clean_text2.replace('\n', ' ').replace(u'\u00a0', " "))
            doc2 = self.nlp(decode_clean_text2)
            for key in api_dic:
                sentence = []
                for sen in doc2.sents:
                    if key in sen.text:
                        sentence.append(sen.text)
                if key in title:
                    sentence.append(title)
                api_qualified_name.append({"ori_api": key,
                                           "qualified_name": api_dic[key],
                                           "alias": self.name_util.generate_aliases(api_dic[key]),
                                           "sentence": sentence,
                                           "processed_sentence": sentence})
            return api_qualified_name

        return oriApiSet

    def extract_api_from_sentence(self, sentence: str, is_title=False, is_completed=False):
        """
        extract api from a sentence, you should declare the source of sentence
        :param sentence:
        :param is_title:
        :return:dic {ori_spi: linked_api}
        """
        oriApiSet = set()
        # punc_pattern = r' |,|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|\(|\)|-|=|\+|，|。|、|；|‘|’|【|】|·|！| ' \
        #                r'|…|（|）'
        punc_pattern = r' |,|/|;|\'|`|\[|\]|<|>|\?|:|"|\{|\}|\~|!|@|#|\$|%|\^|&|-|=|\+|，|。|、|；|‘|’|【|】|·|！| ' \
                       r'|…|（|）'
        # 通常一个句子的首字母会大写，影响驼峰式的结果，一般去除，但是Title中vs类型的大多是api
        raw_words = [word for word in re.split(punc_pattern, sentence) if word]
        if not raw_words:
            return oriApiSet
        if is_title and "vs" in sentence.lower():
            raw_words = raw_words
        else:
            if raw_words[0][0].isupper():
                raw_words = raw_words[1:]
        words = []
        for raw_word in raw_words:
            words.append(raw_word.strip())
        words = set(filter(lambda x: x != '', words))
        for word in words:
            # word = word.lstrip("#(").rstrip(",;.!?")
            if len(word) < 4:
                continue
            # new rule
            if word.endswith("()"):
                oriApiSet.add(word)
                continue
            if word.startswith("(") or word.startswith(")") or word.startswith("www") or word.endswith("com"):
                continue

            # 过滤不规范的单词，比如： .Net , 1.6
            if not word[0].isalpha():
                continue

            url_name = re.match(r"[^[/|\\]+([/|\\][^ ]*)", word)
            if url_name:
                continue

            if ("(" in word and ")" not in word) or (")" in word and "(" not in word):
                continue

            # 排除1.6这种没有字母的单词
            if not bool(re.search('[a-z]', word.lower())):
                continue
            # 排除句子结束末尾的句号，例如: “in Java."
            if word.endswith("."):
                word = word[:-1]

            for index, pattern in enumerate(self.api_patterns):
                search_rs = pattern.search(word)
                if search_rs is not None:
                    # print(index, pattern, search_rs.group("ELE"))
                    oriApiSet.add(word)
        # return dict(zip(list(oriApiSet), [None] * len(oriApiSet)))
        if is_completed:
            post = SOPost(body=None, title=None)
            oriApiSet_new=set()
            for api in oriApiSet:
                completed_api = self.linker.link_one(post, api)
                # 利用so tag过滤
                if completed_api==api and api.lower() in self.so_tag_list:
                    continue
                if len(completed_api.split(".")) == 1 and len(completed_api.split("(")) == 1:
                    continue
                oriApiSet_new.add(api)
            return oriApiSet_new
        return oriApiSet


if __name__ == '__main__':
    recognizer = TextBasedSOPostAPIRecognition()
    text = "Replace a character at a specific index in a string?; I'm trying to replace a character at a specific index in a string.\n ;ANSWER: String are immutable in Java. You can't change them. You need to create a new string with the character replaced. String myName = \"domanokz\"; String newName = myName.substring(0,4)+'x'+myName.substring(5); Or you can use a StringBuilder: StringBuilder myName = new StringBuilder(\"domanokz\"); myName.setCharAt(4, 'x'); System.out.println(myName);"
    oriApiSet = recognizer.extract_api_from_sentence(text, is_title=True)
    print(oriApiSet)
    api_dic = {}
    # oriApiSet = set(api_from_title.keys())
    a = SOPost(body=None, title=None)
    for api in oriApiSet:
        completed_api = recognizer.linker.link_one(post=a, api=api)
        # 过滤一些没用的词，例如驼峰式的Java,Android
        if len(completed_api.split(".")) == 1 and len(completed_api.split("(")) == 1:
            continue
        # completedApiSet.add(completed_api)
        api_dic[api] = completed_api
    print(api_dic)
