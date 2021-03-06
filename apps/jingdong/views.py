#coding:utf-8


from base import BaseHandler

from apps.jingdong.jdAPI import *
from apps.database.databaseCase import *
import json
import re
import tornado.web
import random

import tornado.gen
import tornado.httpclient
from tornado.httpclient import HTTPRequest
import urllib


apiServer = 'http://127.0.0.1:5000'


class JDOrderListHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):

        homePath = self.getHome()

        AUTHOR_MOUDLE = 'ViewJDOrder'

        user = self.current_user
        role = self.get_secure_cookie("role") if self.get_secure_cookie("role") else 'None'

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client

        erp = client.woderp

        account = erp.user.find_one({'account':user})

        authority = self.getAuthority(account,AUTHOR_MOUDLE)

        if authority['Allow']:

            db = client.jingdong

            pageSize = 50

            status = self.get_argument('status','')
            wd = self.get_argument('wd','')
            m = self.get_argument('m','')

            shop = self.get_argument('shop', '')

            try:
                page = int(self.get_argument('page',1))
            except:
                page = 1

            #totalCount = db.orderList.find({"order_state":"WAIT_SELLER_STOCK_OUT"}).count()
            matchOption = dict()
            option = {'platform':'jingdong'}

            if status != '':
                option['order_state'] = status
                matchOption['order_state'] = status


            if authority['role'] == 'Supper':
                shopList = db.shopInfo.find()
            else:
                shopList = db.shopInfo.find({'shopId':{'$in':authority['authority']['jdStore']}})

            if shop != '':
                option['shopId'] = shop
                matchOption['shopId'] = shop
            elif authority['role'] != 'Supper' :
                option['shopId'] = {'$in':authority['authority']['jdStore']}
                matchOption['shopId'] = {'$in':authority['authority']['jdStore']}

            if m == '1':
                option['matchItem'] = { '$exists': True }

            statusList = db.orderList.aggregate(
                [{'$match': matchOption}, {'$group': {'_id': "$order_state", 'orderCount': {'$sum': 1}}}])

            sL = []
            for s in statusList:
                if s['_id']:
                    stxt = ''
                    if s['_id'] == 'WAIT_SELLER_STOCK_OUT':
                        stxt += '待发货'
                    elif s['_id'] == 'SEND_TO_DISTRIBUTION_CENER':
                        stxt += '发往配送中心'
                    elif s['_id'] == 'TRADE_CANCELED':
                        stxt += '已取消'
                    elif s['_id'] == 'RECEIPTS_CONFIRM':
                        stxt += '收款确认'
                    elif s['_id'] == 'WAIT_GOODS_RECEIVE_CONFIRM':
                        stxt += '待收货'
                    elif s['_id'] == 'LOCKED':
                        stxt += '已锁定'
                    elif s['_id'] == 'FINISHED_L':
                        stxt += '已结束'
                    sL.append({'status': s['_id'], 'orderCount': s['orderCount'], 'statusTxt': stxt})


            if wd != '':
                words = re.compile(wd)

                filerList = []
                filerList.append({'item_info_list.sku_name':words})
                filerList.append({'item_info_list.sku_id':words})
                filerList.append({'order_id':words})
                filerList.append({'consignee_info.fullname':words})
                filerList.append({'consignee_info.mobile':words})
                filerList.append({'consignee_info.telephone':words})
                filerList.append({'logisticsInfo.waybill':words})

                option['$or'] = filerList


            totalCount = db.orderList.find(option).count()

            orderList = db.orderList.find(option).sort("order_start_time",-1).limit(pageSize).skip((page-1)*pageSize)

            p = divmod(totalCount,pageSize)

            pageInfo = dict()

            totalPage = p[0]
            if p[1]>0:
                totalPage += 1

            pageInfo['totalPage'] = totalPage
            pageInfo['totalCount'] = totalCount
            pageInfo['pageSize'] = pageSize
            pageInfo['pageNo'] = page
            pageInfo['pageList'] = range(1,totalPage+1)

            filterData = dict()
            filterData['status'] = status
            filterData['shop'] = shop
            filterData['wd'] = wd
            filterData['shopList'] = shopList
            filterData['statusList'] = sL

            self.render('jd/order-list.html',orderList = orderList,homePath=homePath,pageInfo = pageInfo,filterData=filterData,userInfo={'account':user,'role':role})

        else:
            self.render('error/message.html',homePath=homePath, msg={'Msg': 'No Permission', 'Code': 400, 'Title': '无权限！', 'Link': '/'})


class JDSkuListHandler(BaseHandler):
    @tornado.web.authenticated
    def get(self):
        homePath = self.getHome()
        user = self.current_user
        role = self.get_secure_cookie("role") if self.get_secure_cookie("role") else 'None'

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client

        db = client.jingdong

        pageSize = 100

        status = self.get_argument('status', '')
        wd = self.get_argument('wd', '')

        shop = self.get_argument('shop', '')
        shopList = db.shopInfo.find()

        try:
            page = int(self.get_argument('page', 1))
        except:
            page = 1

        matchOption = dict()
        option = {'platform': 'jingdong'}
        if status != '':
            try:
                option['status'] = int(status)
                matchOption['status'] = int(status)
            except:
                pass

        if shop != '':
            option['shopId'] = shop
            matchOption['shopId'] = shop

        statusList = db.skuList.aggregate(
            [{'$match': matchOption}, {'$group': {'_id': "$status", 'itemCount': {'$sum': 1}}}])

        sL = []
        for s in statusList:
            if s['_id']:
                stxt = ''
                if s['_id'] == 1:
                    stxt += '上架'
                elif s['_id'] == 2:
                    stxt += '下架'
                elif s['_id'] == 4:
                    stxt += '删除'

                sL.append({'status': s['_id'], 'itemCount': s['itemCount'], 'statusTxt': stxt})

        if wd != '':
            words = re.compile(wd)

            filerList = []
            filerList.append({'skuId': words})
            filerList.append({'wareTitle': words})
            filerList.append({'skuName': words})
            filerList.append({'wareId': words})

            option['$or'] = filerList

        totalCount = db.skuList.find(option).count()

        skuList = db.skuList.find(option).sort("created", -1).limit(pageSize).skip((page - 1) * pageSize)

        p = divmod(totalCount, pageSize)

        pageInfo = dict()

        totalPage = p[0]
        if p[1] > 0:
            totalPage += 1

        pageInfo['totalPage'] = totalPage
        pageInfo['totalCount'] = totalCount
        pageInfo['pageSize'] = pageSize
        pageInfo['pageNo'] = page
        pageInfo['pageList'] = range(1, totalPage + 1)

        filterData = dict()
        filterData['status'] = status
        filterData['shop'] = shop
        filterData['wd'] = wd
        filterData['shopList'] = shopList
        filterData['statusList'] = sL

        self.render('jd/sku-list.html', skuList=skuList,homePath=homePath, pageInfo=pageInfo, filterData=filterData,
                    userInfo={'account': user, 'role': role})


class JDCheckOrderHandler(BaseHandler):
    @tornado.web.asynchronous
    @tornado.gen.engine
    def get(self):

        #result = o.getOrderList(order_state='WAIT_GOODS_RECEIVE_CONFIRM')

        shopId = self.get_argument('shop', '')
        status = self.get_argument('status', '')
        url = apiServer+"/jd/api/checkOrder?shop=%s&status=%s" % (shopId,status)
        request = HTTPRequest(url=url,method="GET",follow_redirects=False,request_timeout=3000)
        client = tornado.httpclient.AsyncHTTPClient()
        response = yield tornado.gen.Task(client.fetch, request)
        result = json.loads(response.body)
        self.write(result)
        self.finish()



class JDCheckSkuHandler(BaseHandler):

    def get(self):

        shopId = self.get_argument('shop', '')
        sku = self.get_argument('sku','')

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.jingdong

        app = db.shopInfo.find_one({'shopId': shopId})

        data = dict()
        if sku != '' and app != None:

            api = JDAPI(app['apiInfo'])
            result = api.searchSkuList(option={'page_size':'100','skuId':sku,'field':'wareId,skuId,status,jdPrice,outerId,categoryId,logo,skuName,stockNum,wareTitle,created'})
            sl = result['jingdong_sku_read_searchSkuList_responce']['page']['data']
            for s in sl:
                item = s
                item['createTime'] = datetime.datetime.now()
                item['updateTime'] = None
                item['shopId'] = app['shopId']
                item['platform'] = 'jingdong'
                item['stage'] = 0
                item['oprationLog'] = []
                item['skuId'] = str(s['skuId'])
                item['wareId'] = str(s['wareId'])

                try:
                    db.skuList.insert(item)
                except Exception as e:
                    print(e)

            data['success'] = True

        else:
            data['success'] = False

        self.write(json.dumps(data,ensure_ascii=False))


class GetJdSkuImageHandler(BaseHandler):
    def get(self):

        skuId = self.get_argument('skuId','')

        mark = 0
        imgUrl = ''
        if skuId != '':
            mongo = MongoCase()
            mongo.connect()
            client = mongo.client
            db = client.jingdong

            item = db.skuList.find({"skuId":skuId},{"logo":1})
            if item.count()>0:
                imgUrl += item[0]['logo']
                db.orderList.update({'platform':'jingdong',"item_info_list.sku_id":skuId,"item_info_list.skuImg":None},{"$set":{"item_info_list.$.skuImg":item[0]['logo']}})


        if imgUrl == '':
            imgUrl += 'jfs/t3271/88/7808807198/85040/49d5cf69/58bccd95Nd1b090a7.jpg'
            mark += 1

        respon = {'imgUrl': imgUrl,'mark':mark}
        self.write(json.dumps(respon,ensure_ascii=False))


class JdMatchPurchaseOrderHandler(BaseHandler):

    def get(self):
        data = dict()
        ids = self.get_argument('ids', '')
        ids = ids.split(',')
        data['total'] = len(ids)
        data['matchCount'] = 0
        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.jingdong
        woderp = client.woderp
        for orderId in ids:

            order = db.orderList.find_one({'order_id':orderId})


            if order: #and order['order_state'] == 'WAIT_SELLER_STOCK_OUT':


                #purchase = woderp.purchaseList.find({'toFullName':order['consignee_info']['fullname'],'toMobile':order['consignee_info']['mobile'],'createTime':{'$gte':order['createTime']}})
                purchase = woderp.purchaseList.find({'toFullName':order['consignee_info']['fullname'],'toMobile':order['consignee_info']['mobile']})

                if order.has_key('matchStatus') and order['matchStatus']==1 :
                    pass
                else:

                    matchItem = []
                    for item in purchase:
                        matchData = dict()
                        matchData['orderId'] = item['id']
                        matchData['orderStatus'] = item['status']
                        if item.has_key('logistics'):
                            matchData['logistics'] = item['logistics']

                        matchItem.append(matchData)


                    if len(matchItem)>0:
                        data['matchCount'] += 1
                        db.orderList.update({'order_id':orderId},{'$set':{'matchItem':matchItem,'matchStatus':1}})


        self.write(json.dumps(data,ensure_ascii=False))


class JDChcekOrderInfoHanlder(BaseHandler):

    def get(self):
        data = dict()
        orderId = self.get_argument('orderId', '')
        shopId = self.get_argument('shopId', '')

        mongo = MongoCase()
        mongo.connect()
        client = mongo.client
        db = client.jingdong

        app = db.shopInfo.find_one({'shopId': shopId})

        if orderId != '' and app:
            api = JDAPI(app['apiInfo'])

            result = api.getOrderDetail(order_id=orderId,
                                      option={"optional_fields": "order_state,pin,waybill,logistics_id,modified,return_order,order_state_remark,vender_remark,payment_confirm_time"})
            orderInfo = result['order_get_response']['order']['orderInfo']

            item = dict()

            if orderInfo["pin"] != '':
                item['pin'] = orderInfo["pin"]

            logistics = dict()
            if orderInfo["logistics_id"] != '':
                logistics['logistics_id'] = orderInfo["logistics_id"]
                logistics['waybill'] = orderInfo["waybill"]
            if logistics != {}:
                item['logisticsInfo'] = logistics
                item['dealStatus'] = 3
            item['modified'] = orderInfo['modified']
            item['order_state'] = orderInfo['order_state']
            item['return_order'] = orderInfo['return_order']
            item['order_state_remark'] = orderInfo['order_state_remark']
            item['vender_remark'] = orderInfo['vender_remark']
            item['payment_confirm_time'] = orderInfo['payment_confirm_time']
            item['updateTime'] = datetime.datetime.now()

            db.orderList.update({"order_id": orderId}, {'$set': item})

            data['success'] = True
        else:
            data['success'] = False

        self.write(json.dumps(data,ensure_ascii=False))
