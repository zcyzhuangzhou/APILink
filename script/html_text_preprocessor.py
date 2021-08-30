#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/12/19
------------------------------------------
@Modify: 2019/12/19
------------------------------------------
@Description:
"""
import re
import string
import gensim
from bs4 import BeautifulSoup


class HtmlTextPreprocessor:
    pattern = re.compile(r'\s+')
    CODE_FRAGMENT_MARK = "-CODE-"

    def __clean_format(self, text):
        """
        clean text change_data_into_doccano_format for text extract from html
        :param text:
        :return:
        """
        return re.sub(self.pattern, " ", text.replace('\n', ' ').replace(u'\u00a0', " "))

    def clean_html_text(self, html_text,li=True, p=True):

        if html_text is None or len(html_text) == 0:
            return ""

        soup = BeautifulSoup(html_text, "lxml")
        codeTags = soup.find_all(name=["pre", 'blockquote'])

        for tag in codeTags:
            tag.string = " " + self.CODE_FRAGMENT_MARK + " . \n"

        # this is for <li> <ul>

        if li:
            list_groups = soup.find_all(name=["ol", "ul"])
            for list_group in list_groups:
                list_items = list_group.find_all("li")
                num = 1
                for item in list_items:
                    if len(item.get_text().strip()) == 0:
                        continue
                    if item.get_text().strip()[-1] in string.punctuation:
                        item.string = "[{0}]{1}. ".format(str(num), item.get_text())
                        num = num + 1
                        continue
                    item.string = "[{0}]{1}. ".format(str(num), item.get_text())
                    num = num + 1
                    # item.string = item.string + ".\n "

        # this is for <p> ,暂时发现p后添加会导致与原来的分句有冲突，会影响代码的恢复，并且**** -CODE-对这种形式的句子分句有影响,所以先判断它的兄弟节点
        if p:
            p = soup.find_all(name=["p"])
            for item in p:
                # 发现有的<p>是空的，只是为了换行
                if item.get_text().strip():
                    if item.get_text().strip()[-1] in string.punctuation:
                        continue
                    next_sibling = item.find_next_sibling()
                    if next_sibling and self.CODE_FRAGMENT_MARK in next_sibling.get_text():
                        item.string = item.get_text() + ":"
                        continue
                    item.string = item.get_text() + ".\n "


        cleanText = soup.get_text()
        decode_clean_text = gensim.utils.decode_htmlentities(cleanText)
        return self.__clean_format(decode_clean_text)

    def clean_html_text_with_code(self, html_text):
        if html_text is None or len(html_text) == 0:
            return ""

        soup = BeautifulSoup(html_text, "lxml")

        # this is for <li> <ul>
        list_groups = soup.find_all(name=["ol", "ul"])
        for list_group in list_groups:
            list_items = list_group.find_all("li")
            num = 1
            for item in list_items:
                if item.get_text().strip()[-1] in string.punctuation:
                    item.string = "[{0}]{1}\n ".format(str(num), item.get_text())
                    num = num + 1
                    continue
                item.string = "[{0}]{1}.\n ".format(str(num), item.get_text())
                num = num + 1
        # this is for <p> ,暂时发现p后添加会导致与原来的分句有冲突，会影响代码的恢复，并且**** -CODE-对这种形式的句子分句有影响
        p = soup.find_all(name=["p"])
        for item in p:
            # 发现有的<p>是空的，只是为了换行
            if item.get_text():
                if item.get_text().strip()[-1] in string.punctuation:
                    continue
                next_sibling = item.find_next_sibling()
                if next_sibling and self.CODE_FRAGMENT_MARK in next_sibling.get_text():
                    continue
                item.string = item.get_text() + ".\n "
        cleanText = soup.get_text()
        decode_clean_text = gensim.utils.decode_htmlentities(cleanText)
        return self.__clean_format(decode_clean_text)

    def code_restore(self, html, sentence, p=True,pre_num=0):

        """
        return code list from masked sentence
        :param html: original
        :param sentence:  sentence contain "-CODE-"
        :return: code
        """
        if not self.CODE_FRAGMENT_MARK in sentence:
            return []

        text = self.clean_html_text(html, p=p)
        if sentence not in text:
            # print(sentence)
            # print(text)
            return []

        start_index = text.index(sentence)
        #调用的sentence为了唯一识别往前pre_num,需要添加回去，防止CODE. XXXXX:CODE的情况
        start_code_index = text[0:start_index+pre_num].count(self.CODE_FRAGMENT_MARK)
        soup = BeautifulSoup(html, "lxml")
        codeTags = soup.find_all(name=["pre", 'blockquote'])
        code_count = sentence.count(self.CODE_FRAGMENT_MARK)
        code_list = []
        for index in range(start_code_index, start_code_index + code_count):
            code = codeTags[index].get_text()
            if code:
                code_list.append(code)
        return code_list
