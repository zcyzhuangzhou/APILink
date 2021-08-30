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
@Description:
"""
from abc import abstractmethod
from model.base import SOPost


class SOPostAPIRecognition:
    @abstractmethod
    def recognize(self, post: SOPost):
        return set()


class SOPostAPILinker:
    """
    for api mentioned in the SO discussion, complete it into the qualified name
    """

    def link_one(self, post: SOPost, api):
        """
        try to link one api
        :param post:
        :param api: the api need to linked
        :return:
        """
        # todo: need to implement
        return api

    def link_batch(self, post: SOPost, api):
        """
        try to link one api
        :param post:
        :param api: the api need to linked
        :return:
        """
        # todo: need to implement
        return api
