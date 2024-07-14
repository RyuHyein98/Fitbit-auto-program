import os
import numpy as np
import pandas as pd
import datetime
import urllib.request
import urllib.error
import base64
import json
import math
import re
import openpyxl
import sys

import PyQt5
from PyQt5 import QtCore, QtGui, QtWidgets
from PyQt5.QtWidgets import QWidget, QGroupBox, QComboBox, QCheckBox, QButtonGroup, \
    QRadioButton, QPushButton, QLineEdit, QLabel, QFileDialog
from functools import partial

# import matplotlib
import matplotlib.pyplot as plt

import ssl

ssl._create_default_https_context = ssl._create_unverified_context


class DataManager:
    def __init__(self):
        super().__init__()

    # Authorization code 들이 저장된 파일의 path 구함
    def get_aut_path(self):
        file_name = "/Users/hyein/Desktop/fitbit_data_down_system/dist/data/lung_db.csv"
        application_path = ''

        # determine if application is a script file or frozen exe
        if getattr(sys, 'frozen', False):
            application_path = os.path.dirname(sys.executable)
        elif __file__:
            application_path = os.path.dirname(__file__)

        print("application_path = ", application_path)
        aut_path = os.path.join(application_path, file_name)
        print("aut_path = ", aut_path)

        return aut_path

    # file_path = '/Users/sjyoung/PycharmProjects/pyqt/report/201801_patients_data.csv'
    def read_data(self, file_path, index_col):
        file_type = file_path[-3:]
        if file_type == "csv":
            data_table = pd.read_csv(file_path, index_col=index_col, engine='python')
        elif file_type in ["lsx", "xls"]:
            data_table = pd.read_excel(file_path, index_col=index_col)
        else:
            data_table = None

        return data_table

    def save_data(self, data, save_path, save_option):
        file_type = save_path[-3:]

        if file_type not in ["csv", "lsx", "xls"]:
            save_path += "." + save_option

        # 엑셀로 저장
        if save_option == "xlsx":
            with pd.ExcelWriter(save_path) as writer:
                data.to_excel(writer, 'Sheet1', index=False)

        # csv로 저장
        elif save_option == "csv":
            data.to_csv(save_path, index=False)


class Authorization:
    def __init__(self):
        super().__init__()
        self.dm = DataManager()
        self.path = self.dm.get_aut_path()
        self.db = self.dm.read_data(self.path, index_col=0)
        self.redirect_url = 'https://localhost/callback'
        self.id = ''
        self.fitbit_db = self.dm.read_data(self.path, index_col=0)

    def set_id(self, f_id):
        self.id = f_id

    def renew_aut_code(self, f_id, ref_token):
        # f_id = self.fitbit_id
        # Form the data payload
        BodyText = {'grant_type': 'refresh_token', 'refresh_token': ref_token}
        # URL Encode it
        BodyURLEncoded = urllib.parse.urlencode(BodyText)
        # Start the request
        TokenURL = "https://api.fitbit.com/oauth2/token"
        tokenreq = urllib.request.Request(TokenURL, BodyURLEncoded.encode('utf-8'))

        OAuthTwoClientID = self.db.ioc[f_id].loc['client_ID']
        ClientOrConsumerSecret = self.db.loc[f_id].loc['client_sec']
        RedirectURL = self.db.loc[f_id].loc['redirect_url']

        sen = (OAuthTwoClientID + ":" + ClientOrConsumerSecret)
        sentence = base64.b64encode(sen.encode('utf-8'))

        tokenreq.add_header('Authorization', 'Basic ' + sentence.decode('utf-8'))
        tokenreq.add_header('Content-Type', 'application/x-www-form-urlencoded')

        # Fire off the request
        try:
            tokenresponse = urllib.request.urlopen(tokenreq)

            # See what we got back.  If it's this part of  the code it was OK
            self.FullResponse = tokenresponse.read()

            # Need to pick out the access token and write it to the config file.  Use a JSON manipluation module
            ResponseJSON = json.loads(self.FullResponse)

            # Read the access token as a string
            NewAccessToken = str(ResponseJSON['access_token'])
            NewRefreshToken = str(ResponseJSON['refresh_token'])
            # Write the access token to the ini file

            self.db.loc[f_id].loc['acc_token'] = NewAccessToken
            self.db.loc[f_id].loc['ref_token'] = NewRefreshToken

            print("NewAccessToken = ", NewAccessToken)
            print("NewRefreshToken = ", NewRefreshToken)

            self.db.to_csv(self.path)

        except urllib.error.HTTPError as e:
            # Gettin to this part of the code means we got an error
            print("[Error] An error was raised when getting the access token.")
            print("[Error] Need to stop here -", self.p_id, self.f_id)
            print(e.reason)
            # sys.exit()
            pass

    def set_aut_code(self, f_id, body_info):
        if f_id in self.db.index:
            print("============= 이미 등록된 id 입니다 =============")
            return

        info_len = len(body_info)
        if info_len == 5:
            is_new_aut = True
            print("[SET]", f_id, "'s  New Authorization")

        else:
            return

        TokenURL = "https://api.fitbit.com/oauth2/token"

        # BodyText = {'code': aut_code,
        #             'redirect_uri': self.redirect_url,
        #             'client_id': client_id,
        #             'client_sec': client_sec
        #             'grant_type': 'authorization_code'}

        BodyURLEncoded = urllib.parse.urlencode(body_info)
        print(BodyURLEncoded)

        # Start the request
        req = urllib.request.Request(TokenURL, BodyURLEncoded.encode('utf-8'))

        client_id = body_info['client_id']
        client_sec = body_info['client_sec']
        aut_code = body_info['code']
        sen = (client_id + ":" + client_sec)
        sentence = base64.b64encode(sen.encode('utf-8'))

        req.add_header('Authorization', 'Basic ' + sentence.decode('utf-8'))
        req.add_header('Content-Type', 'application/x-www-form-urlencoded')

        try:
            response = urllib.request.urlopen(req)

            full_response = response.read()

            response_json = json.loads(full_response)

            access_token = str(response_json['access_token'])
            refresh_token = str(response_json['refresh_token'])

            if is_new_aut is True:
                # Write the access token to the ini file
                aut_data = [client_id, client_sec, self.redirect_url, access_token, refresh_token, aut_code]
                print(aut_data)
                # db_len = len(self.db)
                # self.db.loc[db_len] = aut_data
                self.db.loc[f_id] = aut_data

                print("============= New Token 저장 완료 - ", f_id, "=============")

            else:
                self.db.loc[f_id].loc['acc_token'] = access_token
                self.db.loc[f_id].loc['ref_token'] = refresh_token

            # self.dm.save_data(self.db, self.path, 'csv')
            self.db.to_csv(self.path)

        except urllib.error.HTTPError as e:
            print("[Error] Token 저장 실패 - ", f_id)
            print('access_token = ', access_token)
            print('refresh_token = ', refresh_token)
            print("client_ID, client_sec, AuthorizationCode 재확인 필요")
            print(e.code)
            print(e.read())



class FitbitData:
    def __init__(self):
        super().__init__()
        self.dm = DataManager()
        self.aut = Authorization()
        self.data_type = ''
        self.f_id = ''
        self.fitbit_id = ''
        self.p_id = ''
        self.p_time = ''
        self.start_date = ''
        self.end_date = ''
        self.minute_type = ''
        self.full_id = ''
        self.acc_token = ''
        self.ref_token = ''
        self.valid_dates = []
        self.non_valid_dates = []
        self.differ_dates_arr = []
        self.sleep_df = pd.DataFrame()
        # 기준 착용기간 (6일 + 여유 5일) # 30일
        self.period_criteria = 31
        self.error_in_API_response = "[Error] fitbit API response is None"
        self.fitbit_db = self.dm.read_data(self.dm.get_aut_path(), index_col=0)  # fitbit_db 초기화

    # Other methods follow...


    # 날짜 형식이 유효한지 체크
    def check_valid_date(self, date):
        if self.isBlank(str(date)) is True:
            return "false"

        date_obj = self.get_date_object(date)

        if isinstance(date_obj, datetime.date):
            return "false"

    # 오늘 날짜를 구한다
    def get_today_date(self):
        today_time = datetime.datetime.now()
        today_date = today_time.strftime('%Y%m%d')

        return today_date

    # 분당 데이터의 총합과 daily step 수의 비교
    def validate_step_data(self, date, sum_data):
        # daily step 데이터 얻어와서 dict 형태로 저장
        url = self.get_activity_url("steps", date, date)
        dict_daily_step = self.get_option_data(date, [url], "crf")
        # dict 형태 ex) dict_daily_step = {'2018-01-30': ['1885']}

        if len(dict_daily_step) > 0:
            daily_step = dict_daily_step[date][0]
            if not isinstance(daily_step, float):
                # 비교를 위해 float 형태로 변경
                daily_step = float(daily_step)

            # 분당 데이터 총합과 데일리 데이터가 다르면 different_dates 배열에 추가
            if self.compare_data(daily_step, sum_data) is False:
                data_gap = float(sum_data - daily_step)
                differ_data = [self.full_id, self.f_id, date, sum_data, daily_step, data_gap]
                self.differ_dates_arr.append(differ_data)
                print("[error report]", self.full_id, date, sum_data, " != ", daily_step, data_gap)

    def compare_data(self, data, target_data):
        comp_result = False

        if type(data) == type(target_data):
            if data == target_data:
                comp_result = True

        return comp_result

    # 여기에서 데이터 타입별로 분기를 시킴
    def classify_data_type(self, data_type, file_path, save_path, save_name, verify_data):
        df = self.dm.read_data(file_path, None)
        print(df)
        if df is not None:
            self.data_type = data_type
            print("[GET]", self.data_type, "data")
            for i, row in df.iterrows():
                p_id = row['PID']
                f_id = row['FID']
                p_time = row['Time']
                start_date = row['StartDate']
                end_date = row['EndDate']

                start_date_obj = self.get_date_object(start_date)
                end_date_obj = self.get_date_object(end_date)

                if not isinstance(end_date_obj, datetime.date):
                    print("[Error - end_date]", end_date_obj, "of", p_id, "is not instance of datetime.date")
                    return

                self.p_id = self.convert_p_id(str(p_id))
                self.f_id = f_id
                self.fitbit_id = self.convert_fitbit_id(f_id)
                self.p_time = int(p_time) if not math.isnan(p_time) else ''

                # lung001_1차_FL001_20160101_20160120_20160201
                self.full_id = str(self.p_id) + '_' + str(self.p_time) + '차_' + self.f_id + '_'\
                               + start_date_obj.strftime('%Y%m%d') + '_' + end_date_obj.strftime('%Y%m%d') + '_'\
                               + self.get_today_date()

                get_msg = "Get " + self.data_type + " data of " + self.full_id
                print("[START]", get_msg)

                # adjust start & end date
                adjusted_dates = self.adjust_dates(start_date_obj, end_date_obj)
                if len(adjusted_dates) == 0:
                    print("[Error - date]", self.p_id, "end_date:", end_date_obj,
                          " - start_date", start_date_obj, ") <= 0")
                    return
                self.start_date = str(adjusted_dates['start_date'])
                self.end_date = str(adjusted_dates['end_date'])

                # get access and reference token
                self.acc_token, self.ref_token = self.get_fitbit_tokens(self.fitbit_id)

                self.non_valid_dates = self.get_non_valid_date()
                self.valid_dates = self.get_valid_dates(self.non_valid_dates)

                # 실제 착용기간(period): 유효날짜 중 첫날 ~ 마지막날
                period = []
                valid_dates_len = len(self.valid_dates)
                if valid_dates_len > 0:
                    valid_start_date = self.get_date_object(self.valid_dates[0]).strftime('%Y%m%d')
                    valid_end_date = self.get_date_object(self.valid_dates[len(self.valid_dates) - 1]).strftime(
                        '%Y%m%d')
                    period = valid_start_date + "-" + valid_end_date
                    print("Valid Period:", [period])

                if self.data_type in ["1min", "15min"]:
                    if valid_dates_len > 0:
                        min_data = self.get_min_data(verify_data)
                        save_name = self.full_id + '_' + self.data_type
                        self.dm.save_data(min_data, save_path + '/' + save_name, "xlsx")
                        print("[SUCCESS]", get_msg)

                    else:
                        print("[No Save] Length of valid dates is 0")

                    if i == (len(df) - 1):
                        print("============= " + self.data_type + " 데이터 다운로드 완료 =============")

                elif self.data_type == "crf":
                    if i == 0:
                        columns = ['id', 'period', 'fitbit_step', 'fitbit_distance', 'fitbit_calories',
                                   'fitbit_activity_calories',
                                   'fitbit_VPA_time', 'fitbit_MPA_time', 'fitbit_LAP_time', 'TAT', 'fitbit_spa_time',
                                   'fitbit_wear_days', 'fitbit_sleep_time', 'fitbit_sleep_wakeup_time',
                                   'fitbit_wakeup_fq', 'fitbit_sleep_bed_time', 'non_valid_dates']
                        crf_data = pd.DataFrame(columns=columns)

                    list_crf_data = self.get_crf_data()
                    if len(list_crf_data) > 0:
                        data_len = len(crf_data)
                        crf_data.loc[data_len] = [self.full_id, period] + list_crf_data
                        print("[SUCCESS]", get_msg)

                    if i == (len(df) - 1):
                        self.dm.save_data(crf_data, save_path + '/' + save_name, "xlsx")
                        print("============= CRF 저장 완료 - ", save_name, ".xlsx =============")

                elif self.data_type == "daily":
                    week_data = self.get_week_data()
                    save_name = self.full_id + '_' + self.data_type
                    self.dm.save_data(week_data, save_path + '/' + save_name, "xlsx")
                    print("[SUCCESS]", get_msg)
                    if i == (len(df) - 1):
                        print("============= " + self.data_type + " 데이터 다운로드 완료 =============")

            if verify_data is True:
                if len(self.differ_dates_arr) > 0:
                    columns = ["id", "f_id", "date", "sum_data", "daily_data", "gap"]
                    df_error_report = pd.DataFrame(self.differ_dates_arr, columns=columns)
                    self.dm.save_data(df_error_report, save_path + '/fitbit_error_report.xlsx', "xlsx")
                    print("=============== error_report 저장 완료 ===============")
                else:
                    print("================= error_report 없음 ==================")

    # 1min/15min data 얻은 후 csv 파일에 저장
    def get_min_data(self, verify_data):
        date_cal = []
        dict_data_value = dict()

        # day 별 1min data 가져와서 csv 파일에 저장
        for idx, date in enumerate(self.valid_dates):
            date_cal.append(date)
            # url request & response
            fitbit_api_url = "https://api.fitbit.com/1/user/-/activities/steps/date/" + date \
                             + "/1d/" + self.data_type + "/time/00:00/23:59.json"
            fitbit_full_res = self.get_api_response(fitbit_api_url)

            if fitbit_full_res is None:
                print(self.error_in_API_response)
                return

            # 정규식 패턴 매칭
            if idx == 0:
                time_value = self.get_time_data(fitbit_full_res)
                dict_data_value['time'] = time_value
            fitbit_data = self.get_value_data(fitbit_full_res, "min")
            dict_data_value[date] = fitbit_data

            if verify_data is True:
                # 분당 데이터 총합 구한 후 데일리 데이터와 비교 검증
                sum_value = self.sum_data(fitbit_data)
                self.validate_step_data(date, sum_value)

        df_data_total = pd.DataFrame.from_dict(dict_data_value)
        # time 이 맨 왼쪽열로 오도록 조정
        df_data_total = df_data_total.reindex(columns=(['time']
                                                       + list([a for a in df_data_total.columns if a != 'time'])))

        return df_data_total

    # activity 데이터 URL Path 얻기
    def get_activity_url(self, option, start_date, end_date):
        if self.isBlank(option) is True:
            print("[Error] option is blank")
            return ''

        url_front = "https://api.fitbit.com/1/user/-/activities/"
        url_end = "/date/" + start_date + "/" + end_date + ".json"

        return url_front + option + url_end

    def get_activity_list(self, date):
        url_front = "https://api.fitbit.com/1/user/-/activities/date/"
        url_end = date + ".json"

        return url_front + url_end

    # sleep 데이터 URL Path 얻기
    def get_sleep_url(self, start_date, end_date):
        url_front = "https://api.fitbit.com/1.2/user/-/sleep"
        url_end = "/date/" + start_date + "/" + end_date + ".json"

        return url_front + url_end

    # CRF 데이터 얻기
    def get_crf_data(self):
        list_total_data = []
        total_activity_time = 0

        # 얻고자 하는 정보들의 url list
        step_options = ["steps", "distance", "calories", "activityCalories", "minutesVeryActive",
                        "minutesFairlyActive", "minutesLightlyActive", "minutesSedentary"]
        sleep_types = ["asleep_minutes", "awake_minutes", "awake_count", "time_in_bed"]

        data_options = step_options + ["sleep"]

        for idx, option in enumerate(data_options):
            valid_values = []

            if option in step_options:
                url = self.get_activity_url(option, self.start_date, self.end_date)

            else:
                url = self.get_sleep_url(self.start_date, self.end_date)

            fitbit_full_res = self.get_api_response(url)

            if fitbit_full_res is None:
                print(self.error_in_API_response)
                return

            # decode 후 json 형태로 변환
            decode_res = fitbit_full_res.decode("utf-8")
            json_res = json.loads(decode_res.replace("'", "\""))

            if option in step_options:
                option_value = json_res['activities-' + option]

                for value in option_value:
                    date_time = value.get('dateTime')
                    if date_time not in self.non_valid_dates:
                        valid_values.append(value)

                fitbit_data = self.get_value_data(json.dumps(valid_values), "crf")

                # 평균 계산
                average_result = self.average_data(fitbit_data)
                average_str = str(average_result)
                list_total_data.append(average_str)

                # TAT(Total Activity Time) 구하기
                if option in ["minutesVeryActive", "minutesFairlyActive", "minutesLightlyActive"]:
                    total_activity_time += average_result

                    if option == 'minutesLightlyActive':
                        list_total_data.append(str(total_activity_time))

            else:
                # fitbit_wear_days 추가
                list_total_data.append(self.get_valid_dates_count(self.non_valid_dates))

                # sleep data
                option_value = json_res['sleep']

                for sleep_type in sleep_types:
                    fitbit_data = self.get_value_data(json.dumps(option_value), sleep_type)

                    # 평균 계산
                    average_result = self.average_data(fitbit_data)
                    average_str = str(average_result)
                    list_total_data.append(average_str)

        list_total_data.append(self.non_valid_dates)

        return list_total_data

    def get_week_data(self):
        # 얻고자 하는 정보들의 url list
        data_options = ["steps", "distance", "calories", "activityCalories", "minutesVeryActive",
                        "minutesFairlyActive", "minutesLightlyActive", "minutesSedentary"]

        week_data_dict = dict()

        for idx, option in enumerate(data_options):
            valid_values = []

            url = self.get_activity_url(option, self.start_date, self.end_date)
            fitbit_full_res = self.get_api_response(url)

            if fitbit_full_res is None:
                print(self.error_in_API_response)
                return

            # decode 후 json 형태로 변환
            decode_res = fitbit_full_res.decode("utf-8")

            json_res = json.loads(decode_res.replace("'", "\""))
            option_value = json_res['activities-' + option]

            # 전체 data 에서 valid date 의 data만 추출
            # sleep data는 valid/non-valid 체크 불필요
            for value in option_value:
                date_time = value.get('dateTime')
                if date_time not in self.non_valid_dates:
                    valid_values.append(value)

            # 정규식 패턴 매칭
            if idx == 0:
                week_data_dict['date'] = self.valid_dates
            fitbit_data = self.get_value_data(json.dumps(valid_values), "crf")

            week_data_dict[option] = fitbit_data

        df_week_data = pd.DataFrame.from_dict(week_data_dict)
        data_options.insert(0, 'date')
        df_week_data = df_week_data.reindex(columns=data_options)
        df_week_data.set_index('date')

        return df_week_data

    def get_option_data(self, cur_date, url_list, data_type):
        dict_data_value = dict()

        for url in url_list:
            fitbit_res = self.get_api_response(url)

            if fitbit_res is not None:
                if data_type == "crf":
                    decode_res = fitbit_res.decode("utf-8")
                    json_res = json.loads(decode_res.replace("'", "\""))
                    option_value = json_res['activities-' + "steps"]
                    fitbit_res = json.dumps(option_value)
                else:
                    time_value = self.get_time_data(fitbit_res)
                    dict_data_value['time'] = time_value

                fitbit_data = self.get_value_data(fitbit_res, data_type)
                dict_data_value[cur_date] = fitbit_data
            else:
                dict_data_value[cur_date] = []  # 빈 데이터 처리

        # 디버깅을 위한 배열 길이 출력
        for key, value in dict_data_value.items():
            print(f"Key: {key}, Length: {len(value)}")

        # Ensure all lists in dict_data_value have the same length and remove empty lists
        lengths = [len(v) for v in dict_data_value.values()]
        if len(set(lengths)) > 1:
            print("Warning: Arrays of different lengths found, adjusting...")
            max_length = max(lengths)
            for key in dict_data_value.keys():
                if len(dict_data_value[key]) < max_length:
                    dict_data_value[key] = [None] * max_length  # Fill with None or appropriate filler

        return dict_data_value

    def get_non_valid_date(self):
        non_valid_dates = []
        valid_dates = []
        dates_list = self.get_valid_dates(non_valid_dates)

        start_time = '08:00:00'
        end_time = '20:00:00'

        # end_date 부터 탐색해서 non_valid_date 일 경우, update_period
        for date in dates_list:
            url = "https://api.fitbit.com/1/user/-/activities/steps/date/" + date + "/1d/15min/time/00:00/23:59.json"
            dict_data_value = self.get_option_data(date, [url], "min")

            # Check if all lists in dict_data_value have the same length
            lengths = [len(v) for v in dict_data_value.values()]
            if len(set(lengths)) > 1:
                print(f"Inconsistent array lengths found for date {date}: {lengths}, adjusting...")
                max_length = max(lengths)
                for key in dict_data_value.keys():
                    if len(dict_data_value[key]) < max_length:
                        dict_data_value[key] = [None] * max_length  # Fill with None or appropriate filler

            if not dict_data_value[date]:  # 데이터가 비어 있을 경우
                non_valid_dates.append(date)
                continue

            df_daily_data = pd.DataFrame.from_dict(dict_data_value)

            if len(df_daily_data) > 0:
                df_daily_data = df_daily_data.set_index(['time'])
                df_daytime = df_daily_data.loc[start_time:end_time]

                non_active_count = 0
                # 활동량 데이터가 4시간 연속 0 일 경우 non_valid_dates 에 추가
                for i, row in df_daytime.iterrows():
                    if row[date] == '0':
                        non_active_count += 1
                        if non_active_count > 16:
                            non_valid_dates.append(date)
                            break
                    else:
                        non_active_count = 0

                valid_dates.append(date)

        return non_valid_dates

    # valid dates 개수 구하기
    def get_valid_dates_count(self, non_valid_dates):
        start_day = self.get_date_object(self.start_date)
        end_day = self.get_date_object(self.end_date)

        day_count = (end_day - start_day).days + 1

        return day_count - len(non_valid_dates)

    # non_valid_dates 를 제외한 valid dates 를 리스트 형태로 가져오기
    def get_valid_dates(self, non_valid_dates):
        valid_dates = []

        start_day = self.get_date_object(self.start_date)
        end_day = self.get_date_object(self.end_date)

        day_count = (end_day - start_day).days + 1

        for i in range(day_count):
            cur_date = (start_day + datetime.timedelta(i)).strftime('%Y-%m-%d')
            if cur_date not in non_valid_dates:
                valid_dates.append(cur_date)

        return valid_dates

    # fitbit_db 에서 token 값 가져오기
    def get_fitbit_tokens(self, fitbit_id):
        ref_token = self.fitbit_db.loc[fitbit_id].loc['ref_token']
        print("fitbit_id = ", fitbit_id, "ref_token = ", ref_token)
        self.GetNewAccessToken(ref_token)
        acc_token = self.fitbit_db.loc[fitbit_id].loc['acc_token']
        ref_token = self.fitbit_db.loc[fitbit_id].loc['ref_token']

        return acc_token, ref_token

    # url 을 넘겨받아 request 보낸 후 response 값을 반환한다
    def get_api_response(self, fitbit_api_url):
        try:
            fitbit_req = urllib.request.Request(fitbit_api_url)
            fitbit_req.add_header('Authorization', 'Bearer ' + self.acc_token)

            fitbit_res = urllib.request.urlopen(fitbit_req)
            fitbit_full_res = fitbit_res.read()

            return fitbit_full_res

        except urllib.error.HTTPError as e:
            print("[HTTP Error] Got this HTTP error: " + str(e.reason))
            print("[HTTP Error] This was in the HTTP error message: " + str(e.code))
            print("[HTTP Error] patient id = ", self.p_id, "fitbit id = ", self.f_id)
            # See what the error was
            if e.code == 401:
                print(self.fitbit_id, "get_api_response token_info = ", self.ref_token)
                self.GetNewAccessToken(self.ref_token)
                print('[HTTP Error] Error code: 401 Try again!')
                # sys.exit()
                pass
            elif e.code == 403:
                print('[HTTP Error] Error code: 403 Forbidden! Invalid authorization')
                # sys.exit()
                pass
            elif e.code == 429:
                print('[HTTP Error] Error code: 429 Too Many Requests! Try again after 1 hour.. ')
                # sys.exit()
                pass

    # 정규식을 이용해 time 값을 찾아 반환한다
    def get_time_data(self, fitbit_res):
        time_pattern = re.compile('\d+:\d+:\d+')
        time_value = time_pattern.findall(fitbit_res.decode("utf-8"))

        return time_value

    # 정규식을 이용해 dateTime 값을 찾아 반환한다
    def get_datetime_data(self, fitbit_res):
        date_pattern = re.compile('"dateTime":"\d+')
        date_value = date_pattern.findall(fitbit_res.decode("utf-8"))

        return date_value

    # 정규식을 이용해 value 값을 찾아 반환한다
    def get_value_data(self, fitbit_res, data_type):
        if self.isBlank(data_type) is True:
            print("[Error] data_type is blank")
            return []

        value_pattern = ''

        if data_type == "min":
            value_pattern = re.compile('"value":\d+')

        elif data_type == "crf":
            value_pattern = re.compile('"value": "\d*\.?\d+"')

        elif data_type == "time_in_bed":
            value_pattern = re.compile('"timeInBed": \d+')

        elif data_type == "asleep_minutes":
            value_pattern = re.compile('"minutesAsleep": \d+')

        elif data_type in ["awake_count", "awake_minutes"]:
            awake_type = data_type.split("_")[1]
            awake_pattern = re.compile('"awake": \{[^{}]*')
            fitbit_res = str(awake_pattern.findall(fitbit_res))
            value_pattern = re.compile('"' + awake_type + '": \d+')

        number_pattern = re.compile('\d*\.?\d+')

        if isinstance(fitbit_res, list):
            fitbit_res = json.dumps(fitbit_res)
        elif isinstance(fitbit_res, bytes):
            fitbit_res = fitbit_res.decode("utf-8")

        fitbit_value = value_pattern.findall(fitbit_res)
        fitbit_data = number_pattern.findall(str(fitbit_value))

        return fitbit_data

    def get_sleep_value(self, fitbit_res):
        time_bed_pattern = re.compile('"timeInBed": \d+')
        awake_pattern = re.compile('"awake": \{[^{}]*')
        count_pattern = re.compile('"count": \d+')
        minute_pattern = re.compile('"minutes": \d+')

        number_pattern = re.compile('\d+')

        # time in bed
        time_bed_value = time_bed_pattern.findall(fitbit_res)
        time_bed_num = number_pattern.findall(str(time_bed_value))

        # awake time & count
        awake_value = awake_pattern.findall(fitbit_res)
        awake_time = minute_pattern.findall(str(awake_value))
        awake_time_num = number_pattern.findall(str(awake_time))
        awake_count = count_pattern.findall(str(awake_value))
        awake_count_num = number_pattern.findall(str(awake_count))

        return {"time_in_bed": time_bed_num, "awake_time": awake_time_num, "awake_count": awake_count_num}

    # data list 들의 평균값 구하기
    def average_data(self, data_list):
        sum_value = self.sum_data(data_list)
        if sum_value > 0:
            average = sum_value / len(data_list)
        else:
            average = 0

        # 반올림이 필요하면 --> round(average, 2)
        return round(average, 2) if average > 0 else average

    # data list 들의 총합 구하기
    def sum_data(self, data_list):
        return sum(float(data) for data in data_list)

    def get_fitbit_type(self, f_id):
        return {
            'FE': 'ego',
            'FL': 'lung',
            'FEL': 'egolung',
            'LEX': 'lungex',
            'R':'R',
            'RCT':'copdrct',
            'LMS':'lungmucle',
            'VCO':'vco',
            'GLC':'gracelc',
            'F': 'copd',
            'INT':'egoint'
        }.get(f_id, f_id)

    # fitbit id 형식 변환 'FE001' -> 'ego001'
    def convert_fitbit_id(self, f_id):
        if self.isBlank(f_id) is True:
            # print("[Error] fitbit_id is blank")
            return ''

        type_pattern = re.compile('\D+')
        cancer_type = type_pattern.findall(f_id)

        num_pattern = re.compile('\d+')
        fitbit_num = num_pattern.findall(f_id)

        if len(cancer_type) > 0 and len(fitbit_num) > 0:
            cancer_type = cancer_type[0]
            fitbit_num = fitbit_num[0]
            fitbit_id = self.get_fitbit_type(cancer_type) + fitbit_num
        else:
            fitbit_id = f_id

        return fitbit_id

    # patient id 형식 변환
    def convert_p_id(self, p_id):
        if self.isBlank(p_id) is True:
            print("[Error] patient_id is blank")
            return ''

        # 공백 제거
        p_id = p_id.strip()

        if self.isNumber(p_id):
            patient_id = 'lung' + str(p_id).zfill(3)
        else:
            patient_id = p_id

        return patient_id

    # 숫자이면 true, 숫자가 아니면 false
    def isNumber(self, string):
        try:
            float(string)
            return True
        except ValueError:
            return False

    # 공백 또는 NULL 이면 true
    def isBlank(self, string):
        return not (string and string.strip())

    # 유효한 날짜 조정
    def adjust_dates(self, start_date_obj, end_date_obj):
        if not (isinstance(start_date_obj, datetime.date) and isinstance(end_date_obj, datetime.date)):
            print("[Error] startDate or endDate is not instance of datetime.date")
            return {}

        # 착용한 날짜와 회수된 날짜의 차이
        delta_days = (end_date_obj - start_date_obj).days

        # 착용 첫날 제외
        start_date = self.add_date(start_date_obj, 1)

        if delta_days > 0:
            if delta_days > self.period_criteria:
                end_date = self.add_date(end_date_obj, self.period_criteria - delta_days)
                print("Original end_date:", end_date_obj, "start_date:", start_date_obj, "delta = ", delta_days)
                print("Adjusted end_date:", end_date)

            else:
                # 착용 마지막날(회수날) 제외
                end_date = self.add_date(end_date_obj, -1)
                print("end_date = ", end_date)
        else:
            # 날짜 차이가 0보다 같거나 작은 경우
            print("[Error] delta_days(end_date - start_date) <= 0")
            return {}

        return {'start_date': start_date, 'end_date': end_date}

    # date 객체 생성
    def get_date_object(self, date, sep="-"):
        if type(date) is datetime.datetime:
            return date.date()
        elif type(date) is pd.Timestamp:
            date = date.strftime("%Y-%m-%d")
        else:
            date = str(date)

        separated_date = date.split(sep)
        # separated_date 가 공백이면 sep="." 으로 다시 수행
        if len(separated_date) < 2:
            sep = "."
            separated_date = date.split(sep)

        try:
            year = int(separated_date[0])
            month = int(separated_date[1])
            day = int(separated_date[2])
            date_obj = datetime.date(year, month, day)
        except ValueError:
            date_obj = datetime.date()

        return date_obj

    # add_value 만큼 날짜 더하기
    def add_date(self, date_obj, add_value):
        return date_obj + datetime.timedelta(days=add_value)

    # 새로운 AccessToken 받기
    def GetNewAccessToken(self, RefToken):
        f_id = self.fitbit_id
        # Form the data payload
        BodyText = {'grant_type': 'refresh_token', 'refresh_token': RefToken}
        # URL Encode it
        BodyURLEncoded = urllib.parse.urlencode(BodyText)
        # Start the request
        TokenURL = "https://api.fitbit.com/oauth2/token"
        tokenreq = urllib.request.Request(TokenURL, BodyURLEncoded.encode('utf-8'))

        OAuthTwoClientID = self.fitbit_db.loc[f_id].loc['client_ID']
        ClientOrConsumerSecret = self.fitbit_db.loc[f_id].loc['client_sec']

        print("OAuthTwoClientID = ", OAuthTwoClientID)
        print("ClientOrConsumerSecret = ", ClientOrConsumerSecret)

        RedirectURL = self.fitbit_db.loc[f_id].loc['redirect_url']

        sen = (OAuthTwoClientID + ":" + ClientOrConsumerSecret)
        sentence = base64.b64encode(sen.encode('utf-8'))

        tokenreq.add_header('Authorization', 'Basic ' + sentence.decode('utf-8'))
        tokenreq.add_header('Content-Type', 'application/x-www-form-urlencoded')

        # Fire off the request
        try:
            tokenresponse = urllib.request.urlopen(tokenreq)

            # See what we got back.  If it's this part of  the code it was OK
            self.FullResponse = tokenresponse.read()

            # Need to pick out the access token and write it to the config file.  Use a JSON manipluation module
            ResponseJSON = json.loads(self.FullResponse)

            # Read the access token as a string
            NewAccessToken = str(ResponseJSON['access_token'])
            NewRefreshToken = str(ResponseJSON['refresh_token'])
            # Write the access token to the ini file

            self.fitbit_db.loc[f_id].loc['acc_token'] = NewAccessToken
            self.fitbit_db.loc[f_id].loc['ref_token'] = NewRefreshToken

            self.fitbit_db.to_csv(self.aut.path)

        except urllib.error.HTTPError as e:
            # Gettin to this part of the code means we got an error
            print("[Error] An error was raised when getting the access token.")
            print("[Error] Need to stop here -", self.p_id, self.f_id)
            print(e.reason)
            # sys.exit()
            pass


class StepChart:
    def __init__(self):
        super().__init__()
        self.start_time = ':00:00'
        self.end_time = ':45:00'
        self.total_arr = []
        self.dm = DataManager()

    def show_data(self, file_path):
        df_total = self.get_dataframe(file_path)
        # print(df_total)
        p_id = self.get_pid(file_path)
        time = self.get_time(file_path)
        x = df_total['time']
        y = df_total['date']
        step = df_total['step']
        colors = df_total['color']
        self.scatter(p_id, time, x, y, step, colors)

    # file_path 에서 patient id 추출
    def get_pid(self, file_path):
        lung_pattern = re.compile('lung\d+')
        ego_pattern = re.compile('ego\d+')

        p_id = lung_pattern.findall(file_path)
        if len(p_id) > 0:
            p_id = p_id[0]
        else:
            p_id = ego_pattern.findall(file_path)
            if len(p_id) > 0:
                p_id = p_id[0]
            else:
                p_id = ''

        return p_id

    # file_path 에서 time 추출
    def get_time(self, file_path):
        time_pattern = re.compile('\d+차')

        time = time_pattern.findall(file_path)
        if len(time) > 0:
            time = time[0]
        else:
            time = ''

        return time

    # 분당데이터를 불러와서 시각화를 위한 데이터로 만들기
    def get_dataframe(self, file_path):
        data = self.dm.read_data(file_path, index_col=0)

        column_values = list(data)
        total_arr = []

        # print(column_values)

        for date in column_values:
            day_data = data[date]

            date = self.change_date_format(date)

            for i in range(24):
                i = str(i)
                if len(i) < 2:
                    i = '0' + i

                # 시간 단위로 데이터 잘라낸 후 sum 계산
                start_time = i + self.start_time
                end_time = i + self.end_time
                hour_data = day_data.loc[start_time:end_time]
                total_step = hour_data.sum()

                # 그래프에 활용하기 위해 10 으로 나눠줌
                preq = total_step / 10
                color = self.get_color(preq)

                arr = [date, i, preq, color]
                total_arr.append(arr)

        df_total = pd.DataFrame(total_arr, columns=['date', 'time', 'step', 'color'])
        return df_total

    # 시각화
    def scatter(self, p_id, time, x, y, size, colors):
        plt.scatter(x, y, s=size, marker='o', color=colors)

        # title 및 label 설정
        self.set_title_label(p_id + ' ' + time + ' - Fitbit Hour-by-Hour', 'hours', 'date')
        plt.xticks(np.arange(0, 24, 1))
        plt.show()

    def set_title_label(self, title, x_label, y_label):
        plt.title(title)
        plt.xlabel(x_label)
        plt.ylabel(y_label)

    # datetime 포맷을 '%Y/%m/%d' 로 변경
    def change_date_format(self, date):
        if isinstance(date, datetime.date):
            date_time = date
        else:
            date_time = datetime.datetime.strptime(date, '%Y-%m-%d')

        date = date_time.strftime('%Y/%m/%d')

        return date

    # 값의 범위에 따라 다른 색상 설정
    # 범위 및 색상은 변경 가능
    def get_color(self, data):
        if data > 200:
            color = '#b72b34'
        elif data > 100:
            color = '#f89f4b'
        elif data > 50:
            color = '#cec64a'
        else:
            color = '#43ad29'

        return color


class Ui_MainWindow(object):
    def __init__(self):
        super().__init__()
        # default 값 설정
        self.font_10 = QtGui.QFont()
        self.font_10.setPointSize(10)
        self.aut = Authorization()
        self.f_data = FitbitData()
        self.step_chart = StepChart()
        self.PATIENTS_TYPES = ['lung', 'ego', 'copd']
        self.FITBIT_TYPES = ['FL', 'FE', 'FEL', 'LEX','R','RCT','VCO','LMS','GLC','F','INT']
        self.redirect_url = 'https://localhost/callback'
        self.TIMES = [str(i) for i in range(0, 9)]

    def setup_ui(self, MainWindow):
        MainWindow.setObjectName("MainWindow")
        MainWindow.resize(800, 600)
        self.centralwidget = QWidget(MainWindow)
        self.centralwidget.setObjectName("centralwidget")
        self.select_group = QGroupBox(self.centralwidget)
        self.select_group.setGeometry(QtCore.QRect(40, 90, 201, 351))
        self.select_group.setObjectName("select_group")
        # crf 데이터
        self.crf_radio_btn = QRadioButton(self.select_group)
        self.crf_radio_btn.setGeometry(QtCore.QRect(30, 60, 130, 22))
        self.crf_radio_btn.setObjectName("save_btn")
        # 분당 데이터
        self.min_radio_btn = QRadioButton(self.select_group)
        self.min_radio_btn.setGeometry(QtCore.QRect(30, 130, 130, 22))
        self.min_radio_btn.setObjectName("min_data_btn")
        # 시각화
        self.show_radio_btn = QRadioButton(self.select_group)
        self.show_radio_btn.setGeometry(QtCore.QRect(30, 200, 130, 22))
        self.show_radio_btn.setObjectName("show_btn")
        # token 등록
        self.token_radio_btn = QRadioButton(self.select_group)
        self.token_radio_btn.setGeometry(QtCore.QRect(30, 270, 130, 22))
        self.token_radio_btn.setObjectName("add_token_btn")

        # radio button 이벤트 연결
        self.token_radio_btn.clicked.connect(self.radio_btn_clicked)
        self.crf_radio_btn.clicked.connect(self.radio_btn_clicked)
        self.min_radio_btn.clicked.connect(self.radio_btn_clicked)
        self.show_radio_btn.clicked.connect(self.radio_btn_clicked)
        self.token_radio_btn.clicked.connect(self.radio_btn_clicked)

        # 새로운 Fitbit 토큰 얻은 후 저장
        self.save_token_group = QGroupBox(self.centralwidget)
        self.save_token_group.setGeometry(QtCore.QRect(260, 90, 491, 351))
        self.save_token_group.setObjectName("save_new_token")
        # fitbit type text
        self.fitbit_type_text = QLabel(self.save_token_group)
        self.fitbit_type_text.setGeometry(QtCore.QRect(30, 38, 100, 30))
        self.fitbit_type_text.setFont(self.font_10)
        self.fitbit_type_text.setObjectName("fitbit_type_text")
        # fitbit type combobox
        self.fitbit_type = QComboBox(self.save_token_group)
        self.fitbit_type.setGeometry(QtCore.QRect(30, 72, 106, 30))
        self.fitbit_type.setObjectName("fitbit_type")
        self.fitbit_type.addItems(self.FITBIT_TYPES)
        # fitbit id text
        self.fitbit_id_text = QLabel(self.save_token_group)
        self.fitbit_id_text.setGeometry(QtCore.QRect(160, 38, 120, 30))
        self.fitbit_id_text.setFont(self.font_10)
        self.fitbit_id_text.setObjectName("fitbit_id_text")
        # fitbit id
        self.fitbit_id = QLineEdit(self.save_token_group)
        self.fitbit_id.setGeometry(QtCore.QRect(160, 72, 130, 30))
        self.fitbit_id.setObjectName("fitbit_id")
        # client id text
        self.client_id_text = QLabel(self.save_token_group)
        self.client_id_text.setGeometry(QtCore.QRect(30, 108, 150, 30))
        self.client_id_text.setFont(self.font_10)
        self.client_id_text.setObjectName("client_id_text")
        # client id
        self.client_id = QLineEdit(self.save_token_group)
        self.client_id.setGeometry(QtCore.QRect(30, 142, 381, 30))
        self.client_id.setObjectName("client_id")
        # client sec text
        self.client_sec_text = QLabel(self.save_token_group)
        self.client_sec_text.setGeometry(QtCore.QRect(30, 178, 150, 30))
        self.client_sec_text.setFont(self.font_10)
        self.client_sec_text.setObjectName("client_sec_text")
        # client sec
        self.client_sec = QLineEdit(self.save_token_group)
        self.client_sec.setGeometry(QtCore.QRect(30, 202, 381, 30))
        self.client_sec.setObjectName("client_sec")
        # Authorization text
        self.aut_text = QLabel(self.save_token_group)
        self.aut_text.setGeometry(QtCore.QRect(30, 248, 150, 30))
        self.aut_text.setFont(self.font_10)
        self.aut_text.setObjectName("aut_text")
        # Authorization
        self.aut_code = QLineEdit(self.save_token_group)
        self.aut_code.setGeometry(QtCore.QRect(30, 272, 381, 30))
        self.aut_code.setObjectName("aut_code")
        # 등록버튼
        self.save_token_btn = QPushButton(self.save_token_group)
        self.save_token_btn.setGeometry(QtCore.QRect(380, 310, 91, 34))
        self.save_token_btn.setFont(self.font_10)
        self.save_token_btn.setObjectName("save_token_btn")
        # body_info = {'code': self.aut_code.text(),
        #              'redirect_uri': self.redirect_url,
        #              'client_id': self.client_id.text(),
        #              'client_sec': self.client_sec.text(),
        #              'grant_type': 'authorization_code'}
        # new_f_id = str(self.fitbit_type.currentText()) + self.fitbit_id.text()
        # print("select id => " + new_f_id)
        # new_fitbit_id = self.f_data.convert_fitbit_id(new_f_id)
        self.save_token_btn.clicked.connect(lambda: self.aut.set_aut_code(
            self.f_data.convert_fitbit_id(self.fitbit_type.currentText() + self.fitbit_id.text()),
            {'code': self.aut_code.text(),
             'redirect_uri': self.redirect_url,
             'client_id': self.client_id.text(),
             'client_sec': self.client_sec.text(),
             'grant_type': 'authorization_code'}))

        # CRF 데이터 다운받은 후 저장
        self.crf_save_group = QGroupBox(self.centralwidget)
        self.crf_save_group.setGeometry(QtCore.QRect(260, 90, 491, 351))
        self.crf_save_group.setObjectName("save_crf_group")
        # crf_file_path_text (Label)
        self.crf_file_path_text = QLabel(self.crf_save_group)
        self.crf_file_path_text.setGeometry(QtCore.QRect(30, 38, 300, 30))
        self.crf_file_path_text.setFont(self.font_10)
        self.crf_file_path_text.setTextFormat(QtCore.Qt.PlainText)
        self.crf_file_path_text.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.crf_file_path_text.setObjectName("label")
        # crf_get_file_btn (Button) - 파일 경로 가져오기 버튼
        self.crf_get_file_btn = QPushButton(self.crf_save_group)
        self.crf_get_file_btn.setGeometry(QtCore.QRect(30, 72, 141, 34))
        self.crf_get_file_btn.setFont(self.font_10)
        self.crf_get_file_btn.setObjectName("get_file_btn")
        # QFileDialog 호출 - 환자기록부 파일 경로 가져오는 Dialog
        self.crf_get_file_btn.clicked.connect(partial(self.get_path_text, "crf_file"))
        # self.crf_get_file_btn.clicked.emit("crf_file")
        # crf_get_file_path (Label) - 불러온 파일 경로 표시
        self.crf_get_file_path = QLabel(self.crf_save_group)
        self.crf_get_file_path.setGeometry(QtCore.QRect(30, 115, 350, 20))
        self.crf_get_file_path.setFont(self.font_10)
        self.crf_get_file_path.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.crf_get_file_path.setObjectName("crf_get_file_path")
        # crf_save_path_text (Label)
        self.crf_save_path_text = QLabel(self.crf_save_group)
        self.crf_save_path_text.setGeometry(QtCore.QRect(30, 150, 300, 30))
        self.crf_save_path_text.setFont(self.font_10)
        self.crf_save_path_text.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.crf_save_path_text.setObjectName("label_2")
        # save_crf_path_btn (Button) - 저장할 폴더 경로 불러오기
        self.crf_save_path_btn = QPushButton(self.crf_save_group)
        self.crf_save_path_btn.setGeometry(QtCore.QRect(30, 185, 141, 34))
        self.crf_save_path_btn.setFont(self.font_10)
        self.crf_save_path_btn.setObjectName("save_file_path")
        # QFileDialog 호출 - 저장할 폴더 경로 불러오는 Dialog
        self.crf_save_path_btn.clicked.connect(partial(self.get_path_text, "crf_folder"))
        # self.crf_save_path_btn.clicked.emit("crf_folder")
        self.crf_save_folder_path = QLabel(self.crf_save_group)
        self.crf_save_folder_path.setGeometry(QtCore.QRect(30, 222, 350, 20))
        self.crf_save_folder_path.setFont(self.font_10)
        self.crf_save_folder_path.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.crf_save_folder_path.setObjectName("crf_save_folder_path")
        # crf_filename_text (Label)
        self.crf_filename_text = QLabel(self.crf_save_group)
        self.crf_filename_text.setGeometry(QtCore.QRect(160, 265, 80, 30))
        self.crf_filename_text.setFont(self.font_10)
        self.crf_filename_text.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.crf_filename_text.setObjectName("label_3")
        # 저장할 파일 이름 입력 (EditText)
        self.crf_file_name = QLineEdit(self.crf_save_group)
        self.crf_file_name.setGeometry(QtCore.QRect(230, 260, 221, 30))
        self.crf_file_name.setText("")
        self.crf_file_name.setObjectName("file_name")
        # 데이터를 불러와서 저장하기 위한 버튼
        self.crf_save_data_btn = QPushButton(self.crf_save_group)
        self.crf_save_data_btn.setGeometry(QtCore.QRect(320, 300, 131, 34))
        self.crf_save_data_btn.setFont(self.font_10)
        self.crf_save_data_btn.setObjectName("save_crf_data")

        self.crf_save_data_btn.clicked.connect(lambda: self.f_data.classify_data_type("crf",
                                                                                      self.crf_get_file_path.text(),
                                                                                      self.crf_save_folder_path.text(),
                                                                                      self.crf_file_name.text(),
                                                                                      False))

        # Fitbit 데이터 시각화
        self.show_group = QGroupBox(self.centralwidget)
        self.show_group.setGeometry(QtCore.QRect(260, 90, 491, 351))
        self.show_group.setObjectName("show_group")
        # 직접 입력 / 불러오기 선택 (radio button)
        self.input_radio = QRadioButton(self.show_group)
        self.input_radio.setGeometry(QtCore.QRect(30, 60, 130, 22))
        self.input_radio.setFont(self.font_10)
        self.input_radio.setObjectName("input_radio")
        self.get_radio = QRadioButton(self.show_group)
        self.get_radio.setGeometry(QtCore.QRect(30, 110, 130, 22))
        self.get_radio.setFont(self.font_10)
        self.get_radio.setObjectName("get_radio")
        # button group에 추가
        self.show_btn_group = QButtonGroup()
        self.show_btn_group.addButton(self.input_radio)
        self.show_btn_group.addButton(self.get_radio)
        # 이벤트 연결
        self.input_radio.clicked.connect(self.show_radio_btn_clicked)
        self.get_radio.clicked.connect(self.show_radio_btn_clicked)
        # patient type text
        self.pat_type_text = QLabel(self.show_group)
        self.pat_type_text.setGeometry(QtCore.QRect(170, 48, 100, 30))
        self.pat_type_text.setFont(self.font_10)
        self.pat_type_text.setObjectName("patient_type_text")
        # patient type combobox
        self.pat_type = QComboBox(self.show_group)
        self.pat_type.setGeometry(QtCore.QRect(170, 82, 100, 30))
        self.pat_type.setObjectName("patient_type")
        self.pat_type.addItems(self.PATIENTS_TYPES)
        # patient id text
        self.pat_id_text = QLabel(self.show_group)
        self.pat_id_text.setGeometry(QtCore.QRect(310, 48, 120, 30))
        self.pat_id_text.setFont(self.font_10)
        self.pat_id_text.setObjectName("patient_id_text")
        # patient id 입력
        self.pat_id = QLineEdit(self.show_group)
        self.pat_id.setGeometry(QtCore.QRect(310, 82, 140, 30))
        self.pat_id.setObjectName("patient_id")
        # fitbit type text
        self.fb_type_text = QLabel(self.show_group)
        self.fb_type_text.setGeometry(QtCore.QRect(170, 118, 100, 30))
        self.fb_type_text.setFont(self.font_10)
        self.fb_type_text.setObjectName("fitbit_type_text")
        # fitbit type combobox
        self.fb_type = QComboBox(self.show_group)
        self.fb_type.setGeometry(QtCore.QRect(170, 152, 100, 30))
        self.fb_type.setObjectName("fitbit_type")
        self.fb_type.addItems(self.FITBIT_TYPES)
        # fitbit id text
        self.fb_id_text = QLabel(self.show_group)
        self.fb_id_text.setGeometry(QtCore.QRect(310, 118, 120, 30))
        self.fb_id_text.setFont(self.font_10)
        self.fb_id_text.setObjectName("fitbit_id_text")
        # fitbit id 입력
        self.fb_id = QLineEdit(self.show_group)
        self.fb_id.setGeometry(QtCore.QRect(310, 152, 140, 30))
        self.fb_id.setObjectName("fitbit_id")
        # 차수 선택 text
        self.time_text = QLabel(self.show_group)
        self.time_text.setGeometry(QtCore.QRect(170, 198, 100, 30))
        self.time_text.setFont(self.font_10)
        self.time_text.setObjectName("time_text")
        # 차수 선택 combobox
        self.time_selection = QComboBox(self.show_group)
        self.time_selection.setGeometry(QtCore.QRect(170, 222, 100, 30))
        self.time_selection.setObjectName("time_selection")
        self.time_selection.addItems(self.TIMES)
        # 날짜 선택
        self.select_date_btn = QPushButton(self.show_group)
        self.select_date_btn.setGeometry(QtCore.QRect(310, 222, 110, 34))
        self.select_date_btn.setFont(self.font_10)
        self.select_date_btn.setObjectName("select_date_btn")
        self.select_date_btn.clicked.connect(self.get_calendar)
        # 미리 저장된 분당 데이터 가져오기
        self.show_get_file_btn = QPushButton(self.show_group)
        self.show_get_file_btn.setGeometry(QtCore.QRect(170, 275, 100, 34))
        self.show_get_file_btn.setFont(self.font_10)
        self.show_get_file_btn.setObjectName("get_file_btn")
        # QFileDialog 호출 - 환자기록부 파일 경로 가져오는 Dialog
        self.show_get_file_btn.clicked.connect(partial(self.get_path_text, "show_file"))
        # show_get_file_path (Label) - 불러온 파일 경로 표시
        self.show_get_file_path = QLabel(self.show_group)
        self.show_get_file_path.setGeometry(QtCore.QRect(275, 275, 100, 30))
        self.show_get_file_path.setFont(self.font_10)
        self.show_get_file_path.setObjectName("show_get_file_path")
        # 데이터 시각화 button
        self.show_graph_btn = QPushButton(self.show_group)
        self.show_graph_btn.setGeometry(QtCore.QRect(380, 310, 100, 34))
        self.show_graph_btn.setFont(self.font_10)
        self.show_graph_btn.setObjectName("show_graph_btn")

        self.show_graph_btn.clicked.connect(lambda: self.step_chart.show_data(self.show_get_file_path.text()))

        # 1분/15분/daily 데이터 다운받은 후 저장
        self.min_save_group = QGroupBox(self.centralwidget)
        self.min_save_group.setGeometry(QtCore.QRect(260, 90, 491, 351))
        self.min_save_group.setObjectName("save_min_group")
        # file path text (Label)
        self.min_file_path_text = QLabel(self.min_save_group)
        self.min_file_path_text.setGeometry(QtCore.QRect(30, 38, 300, 30))
        self.min_file_path_text.setFont(self.font_10)
        self.min_file_path_text.setTextFormat(QtCore.Qt.PlainText)
        self.min_file_path_text.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.min_file_path_text.setObjectName("label_4")
        # get_file_btn (Button) - 파일 경로 가져오기 버튼
        self.min_get_file_btn = QPushButton(self.min_save_group)
        self.min_get_file_btn.setGeometry(QtCore.QRect(30, 72, 141, 34))
        self.min_get_file_btn.setFont(self.font_10)
        self.min_get_file_btn.setObjectName("get_file_btn_2")
        # QFileDialog 호출
        self.min_get_file_btn.clicked.connect(partial(self.get_path_text, "min_file"))
        # min_get_file_path (Label) - 불러온 파일 경로 표시
        self.min_get_file_path = QLabel(self.min_save_group)
        self.min_get_file_path.setGeometry(QtCore.QRect(30, 115, 350, 30))
        self.min_get_file_path.setFont(self.font_10)
        self.min_get_file_path.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.min_get_file_path.setObjectName("min_get_file_path")
        # 1분/15분 선택 (RadioButton)
        self.one_min_select = QRadioButton(self.min_save_group)
        self.one_min_select.setGeometry(QtCore.QRect(30, 170, 130, 22))
        self.one_min_select.setFont(self.font_10)
        self.one_min_select.setObjectName("1min")
        self.fif_min_select = QRadioButton(self.min_save_group)
        self.fif_min_select.setGeometry(QtCore.QRect(30, 220, 130, 22))
        self.fif_min_select.setFont(self.font_10)
        self.fif_min_select.setObjectName("15min")
        self.daily_select = QRadioButton(self.min_save_group)
        self.daily_select.setGeometry(QtCore.QRect(30, 270, 130, 22))
        self.daily_select.setFont(self.font_10)
        self.daily_select.setObjectName("daily")
        # ButtonGroup 에 min 선택하는 라디오 버튼 추가
        self.min_btn_group = QButtonGroup()
        self.min_btn_group.addButton(self.one_min_select)
        self.min_btn_group.addButton(self.fif_min_select)
        self.min_btn_group.addButton(self.daily_select)
        # save_min_path_btn - 저장 폴더 경로 가져오기 버튼
        self.min_save_path_btn = QPushButton(self.min_save_group)
        self.min_save_path_btn.setGeometry(QtCore.QRect(130, 202, 141, 34))
        self.min_save_path_btn.setFont(self.font_10)
        self.min_save_path_btn.setObjectName("save_file_path_2")
        # QFileDialog 호출
        self.min_save_path_btn.clicked.connect(partial(self.get_path_text, "min_folder"))
        # min_get_folder_path (Label) - 저장할 폴더 경로 표시
        self.min_save_folder_path = QLabel(self.min_save_group)
        self.min_save_folder_path.setGeometry(QtCore.QRect(130, 243, 300, 30))
        self.min_save_folder_path.setFont(self.font_10)
        self.min_save_folder_path.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.min_save_folder_path.setObjectName("min_path_label")
        # min_save_path_text (Label)
        self.min_save_path_text = QLabel(self.min_save_group)
        self.min_save_path_text.setGeometry(QtCore.QRect(130, 168, 350, 30))
        self.min_save_path_text.setFont(self.font_10)
        self.min_save_path_text.setAlignment(QtCore.Qt.AlignBottom | QtCore.Qt.AlignLeading | QtCore.Qt.AlignLeft)
        self.min_save_path_text.setObjectName("label_5")
        # 데이터 검증 여부 선택 (CheckBox)
        self.verify_check = QCheckBox(self.min_save_group)
        self.verify_check.setGeometry(QtCore.QRect(230, 310, 116, 22))
        self.verify_check.setObjectName("verify_check")
        # 최종 데이터 저장버튼
        self.min_save_data_btn = QPushButton(self.min_save_group)
        self.min_save_data_btn.setGeometry(QtCore.QRect(320, 300, 131, 34))
        self.min_save_data_btn.setFont(self.font_10)
        self.min_save_data_btn.setObjectName("save_min_data_btn")

        self.min_save_data_btn.clicked.connect(lambda: self.f_data.classify_data_type(
            self.min_btn_group.checkedButton().objectName(),
            self.min_get_file_path.text(),
            self.min_save_folder_path.text(), '',
            self.verify_check.isChecked()))

        MainWindow.setCentralWidget(self.centralwidget)

        self.retranslateUi(MainWindow)
        self.save_token_group.setHidden(True)
        self.crf_save_group.setHidden(True)
        self.min_save_group.setHidden(True)
        self.show_group.setHidden(True)

        QtCore.QMetaObject.connectSlotsByName(MainWindow)

    def retranslateUi(self, MainWindow):
        _translate = QtCore.QCoreApplication.translate
        MainWindow.setWindowTitle(_translate("MainWindow", "MainWindow"))
        self.select_group.setTitle(_translate("MainWindow", "목적 선택"))
        self.crf_radio_btn.setText(_translate("MainWindow", "CRF 저장"))
        self.min_radio_btn.setText(_translate("MainWindow", "분당 데이터"))
        self.show_radio_btn.setText(_translate("MainWindow", "시각화"))
        self.token_radio_btn.setText(_translate("MainWindow", "Token 등록"))
        # CRF 저장
        self.crf_save_group.setTitle(_translate("MainWindow", "CRF 데이터 불러오기"))
        self.crf_save_data_btn.setText(_translate("MainWindow", "데이터 저장"))
        self.crf_file_path_text.setText(_translate("MainWindow", "환자기록부 파일(.csv 또는 .xlsx)"))
        self.crf_save_path_text.setText(_translate("MainWindow", "Fitbit 데이터 저장 경로"))
        self.crf_filename_text.setText(_translate("MainWindow", "파일명"))
        self.crf_get_file_btn.setText(_translate("MainWindow", "파일 불러오기"))
        self.crf_save_path_btn.setText(_translate("MainWindow", "저장 위치 설정"))
        # 1분/15분/일일 데이터 저장
        self.min_save_group.setTitle(_translate("MainWindow", "1분/15분 데이터 불러오기"))
        self.min_get_file_btn.setText(_translate("MainWindow", "파일 불러오기"))
        self.min_file_path_text.setText(_translate("MainWindow", "환자기록부 파일(.csv 또는 .xlsx)"))
        self.one_min_select.setText(_translate("MainWindow", "1분"))
        self.fif_min_select.setText(_translate("MainWindow", "15분"))
        self.daily_select.setText(_translate("MainWindow", "일일"))
        self.min_save_path_btn.setText(_translate("MainWindow", "저장 폴더 설정"))
        self.min_save_path_text.setText(_translate("MainWindow", "Fitbit 분당 데이터 저장 폴더 경로"))
        self.min_save_data_btn.setText(_translate("MainWindow", "데이터 저장"))
        self.verify_check.setText(_translate("MainWindow", "검증"))
        # 데이터 시각화
        self.show_group.setTitle(_translate("MainWindow", "데이터 시각화"))
        self.input_radio.setText(_translate("MainWindow", "직접 입력"))
        self.get_radio.setText(_translate("MainWindow", "불러오기"))
        self.show_graph_btn.setText(_translate("MainWindow", "데이터 시각화"))
        self.select_date_btn.setText(_translate("MainWindow", "날짜선택"))
        self.show_get_file_btn.setText(_translate("MainWindow", "분당 데이터"))
        self.pat_type_text.setText(_translate("MainWindow", "환자 유형"))
        self.pat_id_text.setText(_translate("MainWindow", "환자 번호 (3자리 숫자)"))
        self.fb_type_text.setText(_translate("MainWindow", "Fitbit 유형"))
        self.fb_id_text.setText(_translate("MainWindow", "Fitbit 번호 (3자리 숫자)"))
        self.time_text.setText(_translate("MainWindow", "차수"))
        # Token 저장
        self.fitbit_type_text.setText(_translate("MainWindow", "Fitbit 유형"))
        self.fitbit_id_text.setText(_translate("MainWindow", "Fitbit 번호 (3자리 숫자)"))
        self.client_id_text.setText(_translate("MainWindow", "Client id 입력"))
        self.client_sec_text.setText(_translate("MainWindow", "Client sec 입력"))
        self.aut_text.setText(_translate("MainWindow", "Authorization code 입력"))
        self.save_token_btn.setText(_translate("MainWindow", "등록"))

    def radio_btn_clicked(self):
        self.save_token_group.setHidden(True)
        self.crf_save_group.setHidden(True)
        self.min_save_group.setHidden(True)
        self.show_group.setHidden(True)

        if self.crf_radio_btn.isChecked():
            self.crf_save_group.show()

        elif self.min_radio_btn.isChecked():
            self.min_save_group.show()

        elif self.show_radio_btn.isChecked():
            self.show_group.show()

        elif self.token_radio_btn.isChecked():
            self.save_token_group.show()

    def show_radio_btn_clicked(self):
        if self.input_radio.isChecked():
            self.show_get_file_btn.setDisabled(True)
            self.pat_type.setDisabled(False)
            self.pat_id.setDisabled(False)
            self.fb_type.setDisabled(False)
            self.fb_id.setDisabled(False)
            self.time_selection.setDisabled(False)
            self.select_date_btn.setDisabled(False)

        elif self.get_radio.isChecked():
            self.show_get_file_btn.setDisabled(False)
            self.pat_type.setDisabled(True)
            self.pat_id.setDisabled(True)
            self.fb_type.setDisabled(True)
            self.fb_id.setDisabled(True)
            self.time_selection.setDisabled(True)
            self.select_date_btn.setDisabled(True)

    def get_calendar(self):
        dlg = ui_dialog()
        dlg.exec_()

    def get_path_text(self, path_type):
        type_arr = path_type.split('_')
        data_type = type_arr[0]
        command_type = type_arr[1]

        if command_type == 'file':
            file_name = QFileDialog.getOpenFileName(MainWindow)
            if data_type == 'crf':
                self.crf_get_file_path.setText(file_name[0])
            elif data_type == 'min':
                self.min_get_file_path.setText(file_name[0])
            elif data_type == "show":
                self.show_get_file_path.setText(file_name[0])

        elif command_type == 'folder':
            folder_name = QFileDialog.getExistingDirectory(MainWindow)
            if data_type == 'crf':
                self.crf_save_folder_path.setText(folder_name)
            elif data_type == 'min':
                self.min_save_folder_path.setText(folder_name)


if __name__ == "__main__":
    import sys
    app = QtWidgets.QApplication(sys.argv)
    MainWindow = QtWidgets.QMainWindow()
    ui = Ui_MainWindow()
    ui.setup_ui(MainWindow)
    MainWindow.show()
    sys.exit(app.exec_())


class ui_dialog(QtWidgets.QDialog):
    def __init__(self):
        super().__init__()
        self.start_date = '2018-01-01'
        self.end_date = '2018-01-01'
        self.setup_ui()

    def setup_ui(self):
        # label
        self.start_date_lbl = QtWidgets.QLabel("Start date", self)
        self.end_date_lbl = QtWidgets.QLabel("End date", self)

        self.select_btn = QtWidgets.QPushButton("Select", self)
        self.select_btn.clicked.connect(self.select_event)

        self.cancel_btn = QtWidgets.QPushButton("Cancel", self)
        self.cancel_btn.clicked.connect(self.close)

        self.start_date_label = QtWidgets.QLabel(self)
        self.end_date_label = QtWidgets.QLabel(self)

        self.start_cal = QtWidgets.QCalendarWidget(self)
        self.start_cal.setVerticalHeaderFormat(0)
        self.start_cal.setFixedSize(self.start_cal.sizeHint())
        self.start_cal.clicked.connect(self.show_start_date)

        self.end_cal = QtWidgets.QCalendarWidget(self)
        self.end_cal.setVerticalHeaderFormat(0)
        self.end_cal.setFixedSize(self.end_cal.sizeHint())
        self.end_cal.clicked.connect(self.show_end_date)

        leftlayout = QtWidgets.QVBoxLayout()
        leftlayout.addWidget(self.start_date_lbl)
        leftlayout.addWidget(self.start_date_label)
        leftlayout.addWidget(self.start_cal)
        leftlayout.addWidget(self.select_btn)

        rightlayout = QtWidgets.QVBoxLayout()
        rightlayout.addWidget(self.end_date_lbl)
        rightlayout.addWidget(self.end_date_label)
        rightlayout.addWidget(self.end_cal)
        rightlayout.addWidget(self.cancel_btn)

        hbox = QtWidgets.QHBoxLayout()
        hbox.addLayout(leftlayout)
        hbox.addLayout(rightlayout)

        self.setLayout(hbox)

        self.setGeometry(100, 100, 200, 200)

    def show_start_date(self):
        temp_date = self.start_cal.selectedDate()
        self.start_date = str(temp_date.toPyDate())
        self.start_date_label.setText(self.start_date)

    def show_end_date(self):
        temp_date = self.end_cal.selectedDate()
        self.end_date = str(temp_date.toPyDate())
        self.end_date_label.setText(self.end_date)

    def select_event(self):
        ui.start_date = self.start_date
        ui.end_date = self.end_date
        ui.Send_Button.setEnabled(True)
        self.close()
