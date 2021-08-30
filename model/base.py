#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
-----------------------------------------
@Author: zhaocy
@Email: 19110240027@fudan.edu.cn
@Created: 2019/10/28
------------------------------------------
@Modify: 2019/10/28
------------------------------------------
@Description: the basic model file
"""
from gensim.utils import SaveLoad
from sekg.ir.doc.wrapper import MultiFieldDocumentCollection, MultiFieldDocument

from script.html_text_preprocessor import HtmlTextPreprocessor


class SOPost:
    def __init__(self, body, title, id=None, post_type_id=1, accepted_answer_id=None, parent_id=None, score=0,
                 view_count=None, owner_user_id=None,
                 last_editor_user_id=None, last_edit_date=None, last_activity_date=None, tags=None, answer_count=None,
                 comment_count=None, favorite_count=None, creation_date=None):
        self.id = id
        self.post_type_id = post_type_id
        self.accepted_answer_id = accepted_answer_id
        self.parent_id = parent_id
        self.score = score
        self.view_count = view_count
        self.body = body
        self.owner_user_id = owner_user_id
        self.last_editor_user_id = last_editor_user_id
        self.last_edit_date = last_edit_date
        self.last_activity_date = last_activity_date
        self.title = title
        self.tags = tags
        self.answer_count = answer_count
        self.comment_count = comment_count
        self.favorite_count = favorite_count
        self.creation_date = creation_date

    def __hash__(self):
        """
        the hash value to make this object could be used in set.
        :return:
        """
        return hash(self.id)

    def __eq__(self, other):
        if self.id == other.id:
            return True
        return False

    def __repr__(self):
        return "<SOPost id=%r>" % self.id


class SOQAPair:
    def __init__(self, question: SOPost, answer: SOPost):
        self.question = question
        self.answer = answer

    def __repr__(self):
        return "question=%r answer=%r" % (self.question, self.answer)


class SOPostCollection(SaveLoad):
    """
    A collection for SO post info. include the post basic properties and
    its document(title,body(html),body_clean,...)
    """
    POST_DOC_FIELD_TITLE = "title"
    POST_DOC_FIELD_BODY = "body"
    POST_DOC_FIELD_CLEAN_BODY = "clean_body"

    # todo: add method for support get a qa pair.
    def __init__(self):
        self.id2post = {}
        self.post_doc_collection = MultiFieldDocumentCollection()

    def get_post_ids(self):
        return self.id2post.keys()

    def get_qa_pair_by_question_id(self, question_id):
        question_post: SOPost = self.get_post(question_id)
        if not question_post:
            print("no such question post")
            return None
        answer_id = question_post.accepted_answer_id
        answer_post: SOPost = self.get_post(answer_id)
        if not answer_post:
            print("question post {} has no accepted answer".format(question_id))
            return None
        qa_pair = SOQAPair(question=question_post, answer=answer_post)
        return qa_pair

    def add_post(self, post: SOPost):
        if post is None:
            return False
        self.id2post[post.id] = post
        self.__add_post_doc(post)
        return True

    def __add_post_doc(self, post: SOPost):
        post_doc = MultiFieldDocument(id=post.id, name=post.title)
        clean_body = self.generate_clean_body(post.body)
        post_doc.add_field(SOPostCollection.POST_DOC_FIELD_TITLE, post.title)
        post_doc.add_field(SOPostCollection.POST_DOC_FIELD_CLEAN_BODY, clean_body)
        self.post_doc_collection.add_document(post_doc)

    def get_post_doc(self, post_id):
        return self.post_doc_collection.get_by_id(post_id)

    def get_post_body(self, post_id):
        """
        get the html body of post
        :param post_id: the id of the post
        :return: the SOPost object
        """

        doc: MultiFieldDocument = self.get_post_doc(post_id=post_id)
        return doc.get_doc_text_by_field(SOPostCollection.POST_DOC_FIELD_CLEAN_BODY)

    def get_post_clean_body(self, post_id):
        """
        get the html body of post
        :param post_id: the id of the post
        :return: the SOPost object
        """

        doc: MultiFieldDocument = self.get_post_doc(post_id=post_id)

        if SOPostCollection.POST_DOC_FIELD_CLEAN_BODY in doc.get_field_set():
            return doc.get_doc_text_by_field(SOPostCollection.POST_DOC_FIELD_CLEAN_BODY)
        return self.generate_clean_body(self.get_post_body(post_id))

    def get_post(self, post_id):
        """
        get a post by id
        :param post_id: the post
        :return:the post
        """
        return self.id2post.get(post_id, None)

    def sub_collection(self, post_ids):
        """
        get a sub post collection with given post
        :param post_ids: the post id list or set must in the new sub collection
        :return: a smaller sub SOPostCollection object with given posts
        """
        subcollection = SOPostCollection()
        for post_id in post_ids:
            subcollection.add_post(self.get_post(post_id))
        return subcollection

    def size(self):
        return len(self.id2post.keys())

    def preprocess_all_posts(self):
        """
        preprocess all post in the collection
        :return:
        """
        for post_id in self.get_post_ids():
            self.preprocess_post_body(post_id)

    def preprocess_post_body(self, post_id):
        """
        preprocess one post body in the collection and cache the result.
        :param post_id: the post id need to post
        :return:
        """
        post = self.get_post(post_id)
        if post is None:
            return

        body_html_text = post.body
        body_clean_text = self.generate_clean_body(body_html_text)

        self.post_doc_collection.add_field_to_doc(doc_id=post.id,
                                                  field_name=SOPostCollection.POST_DOC_FIELD_CLEAN_BODY,
                                                  value=body_clean_text)

    @staticmethod
    def generate_clean_body(body_html_text):
        """
        parse one post text in to clean post text, remove all the code and quote textl
        :param body_html_text:
        :return: clean text.
        """
        ##todo: ask xss, we has the code for clean the post html and get the text
        # soup_post = BeautifulSoup(body_html_text, 'lxml')
        #
        # body_clean_text = soup_post.get_text()
        processor = HtmlTextPreprocessor()
        body_clean_text = processor.clean_html_text(body_html_text)
        return body_clean_text
