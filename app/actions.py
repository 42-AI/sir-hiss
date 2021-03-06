import time
import random
from datetime import datetime
from datetime import date
from datetime import timedelta

from config import get_env
from app.utils.gappshelper import GappsHelper
from app.utils.schedulehelper import ScheduleHelper
from app.utils.langhelper import LangHelper

from config import get_env
from config.env import app_env

environment = app_env[get_env('APP_ENV')]

"""Actions class Explainations

This module list all the actions the Slack Bot can do related to the 
/bootcamp_python slash command, is can be tested using the worker.py, 
but the main purpose of the class Actions is to interact with a flask api 
described in __init__.py.

Actions functions:
    help() : return a helper with a list of all available commands 
    and a short description for each command.
        * @return (str)

    register() : register the user to the bootcamp python if it
    is not yet registered, and if authorized by the schedule.
    Check if the command has beed triggered by slack.
        * @gsheet (insert user row on top)
        * @return (str)

    unregister() : unregister the user to the bootcamp python if it
    is already registered, and if authorized by the schedule.
    Check if the command has beed triggered by slack.
        * @gsheet (remove user row)
        * @return (str)

    subject(args) : register a user to a day, if he is already
    registed to the bootcamp, and not yet registered to the day,
    and if authorized by the schedule.
    Send aso the PDF of the day to the user via a private message.
    Check if the command has beed triggered by slack.
        * @gsheet (put PDF in user row at the day column)
        * @return (str)
    
    correction(args) : register a user to a correction for a specific 
    day, if he is already registed to the bootcamp, and also registered
    to the day, but not yet registered for a correction on this day,
    and also not yet attributed for a correction on this day.
    Send aso the PDF of the day to the user via a private message.
    Check if the command has beed triggered by slack.
    It's also checkout if someone is also looking for a correction for the
    same day, if yes, then connect the 2 users to schedule a correction and
    add the user_login of each other to their day cell.
    Send a private message to the 2 users if a match occured.
        * @gsheet (put WAITING/user_login in user row at the day column)
        * @return (str)

    info() : return info about the current user related to the bootcamp_python
    Check if the command has beed triggered by slack.
        * @return (str)

Available utils wrappers:


Todo:
    * [x]: help
    * [x]: register
    * [x]: unregister
    * [x]: subject
    * [x]: correction
    * [x]: info
    * [ ]: French text -> match success double message

"""

def mandatoryUserInfo(f):
    def wrapper(self, *args, **kwargs):
        if self.user_info is None:
            return self.msg.not_logged
        return f(self, *args, **kwargs)

    return wrapper

def mandatoryRegistered(f):
    def wrapper(self, *args, **kwargs):
        for row in self.sheet.get_all_records():
            if row["user_id"] == self.user_id:
                break
        else:
            return self.msg.not_registered
        return f(self, *args, **kwargs)

    return wrapper

def correctDayArgument(f):
    def wrapper(self, *args, **kwargs):
        days = [
            'day00',
            'day01',
            'day02',
            'day03',
            'day04'
        ]
        command = args[0]
        if len(command) != 2:
            return self.msg.err_nbarg
        if command[1] not in days:
            return self.msg.err_fmtarg.format(days)
        return f(self, *args, **kwargs)
    
    return wrapper


class Actions:
    def __init__(self, slackhelper, user_info=None, bootcamp=None):
        self.bootcamp = bootcamp
        self.gappshelper = GappsHelper(bootcamp)
        self.schedule = ScheduleHelper(bootcamp)
        self.sheet = self.gappshelper.open_sheet()
        self.user_info = user_info
        self.slackhelper = slackhelper
        self.msg = LangHelper(lang='fr', bootcamp=bootcamp)
        self.user_name = (
            user_info["user"]["name"]
            if user_info is not None
            and user_info.get("user") is not None
            and user_info["user"].get("name") is not None
            else None
        )
        self.user_id = (
            user_info["user"]["id"]
            if user_info is not None
            and user_info.get("user") is not None
            and user_info["user"].get("id") is not None
            else None
        )

    def help(self):
        text_detail = self.msg.helper
        return text_detail

    @mandatoryUserInfo
    def register(self):
        # Check if the user is already registered
        for row in self.sheet.get_all_records():
            if row["user_id"] == self.user_id: # and not environment.DEBUG:
                return self.msg.allready_registered
        if not self.schedule.can_register():
            return self.msg.not_available
        # Update with user info
        self.sheet.insert_row([self.user_name, self.user_id], 2)
        return self.msg.registration_success

    @mandatoryUserInfo
    @mandatoryRegistered
    def unregister(self):
        if not self.schedule.can_register():
            return self.msg.not_available
        for index, row in enumerate(self.sheet.get_all_records()):
            if row["user_id"] == self.user_id:
                break
        else:
            return self.msg.not_registered
        index += 2
        self.sheet.delete_row(index)
        return self.msg.unregistration_success


    @mandatoryUserInfo
    @mandatoryRegistered
    @correctDayArgument
    def subject(self, args):
        if not self.schedule.can_fetchday(args[1]) and not environment.DEBUG:
            return self.msg.not_available
        day = args[1]
        filename = f"{day}.zip"
        self.slackhelper.pdf_upload(
            f"app/assets/{self.bootcamp}/{filename}",
            filename,
            channel=self.user_id,
            title=day,
        )
        column = self.sheet.find(day).col
        row = self.sheet.find(self.user_id).row
        if self.sheet.cell(row, column).value == '':
            self.sheet.update_cell(row, column, 'PDF')
        return self.msg.subject_success

    @mandatoryUserInfo
    @mandatoryRegistered
    @correctDayArgument
    def correction(self, args):
        day = args[1]
        column = self.sheet.find(day).col
        row = self.sheet.find(self.user_id).row
        requester_cell = self.sheet.cell(row, column)

        def find_partner(column, requester_row):
            waiting_cells = self.sheet.findall("WAITING")
            # random.shuffle(waiting_cells)
            for cell in waiting_cells:
                if cell.col == column and cell.row != requester_row :
                    return cell
            return None

        if requester_cell.value == '':
            return self.msg.notdwl_subject.format(day)
        elif requester_cell.value == 'PDF' or requester_cell.value == 'WAITING':
            partner_cell = find_partner(column, row)
            if partner_cell is None:
                requester_cell.value = 'WAITING'
                self.sheet.update_cells([requester_cell])
                return self.msg.already_inpool
            else:
                partner_user_name = self.sheet.cell(partner_cell.row, 1).value
                partner_user_id = self.sheet.cell(partner_cell.row, 2).value
                partner_cell.value = self.user_name
                requester_cell.value = partner_user_name
                # self.sheet.update_cells([requester_cell, partner_cell])
                self.sheet.update_cell(row, column, partner_user_name)
                self.sheet.update_cell(partner_cell.row, column, self.user_name)
                resp = self.slackhelper.introduce_correctors(self.user_id, partner_user_id, day, self.msg.match_message)
                if resp['ok'] is False:
                    return resp['error']
                return self.msg.correctionmatch_success.format(partner_user_name)
        else:
            return self.msg.already_matched.format(requester_cell.value, day)


    @mandatoryUserInfo
    @mandatoryRegistered
    def info(self):
        def get_day_info(user_id, day):
            row = self.sheet.find(self.user_id).row
            column = self.sheet.find(day).col
            status = self.sheet.cell(row, column).value
            if status == '':
                return "Not started"
            elif status == 'PDF':
                return "Started"
            elif status == 'WAITING':
                return "Waiting for correction"
            else:
                return f"Corrected by {status}"
        
        days = [
                'day00',
                'day01',
                'day02',
                'day03',
                'day04'
            ]
        text_detail = self.msg.info.format(
            self.user_name, self.user_id,
            "\n".join(["\t* {}:  {}".format(day, get_day_info(self.user_id, day)) for day in days])
        )
        return text_detail

    def notify_channel(self):
        text_detail = "*Task #TEST for cmaxime:*"
        self.slackhelper.post_message_to_channel(text_detail)

    
### TO BE COMPLETED ---- SHOULD BE SENT AUTOMATICALLY TO NEWCOMERS
    "Greet any new member on the 42AI Slack"
    def onboarding(self):
        message = "Bienvenue chez 42AI !\
Je me présente, Père Siffleur, je suis le bot de l'association (et un python par la même occasion....)\n\
Mes plus sincères félicitations, car tu es désormais *membre interne* de 42AI. Cet environnement Slack nous sert comme principal moyen de communication, donc n'hésite pas l'ajouter à ton application Slack mobile et sur ton poste de travail !\n\
\n\
Je t'invite à parcourir les différents *channels* selon tes intérêts. Jette un oeil régulièrement au channel #announcements pour les dernières activités. Tu peux aussi poser tes questions sur le channel #general.\n\
\n\
Et suis-nous sur nos *réseaux sociaux* ! :\n\
    - Notre chaîne Youtube : https://www.youtube.com/channel/UCFPZEmP0QSccHq9vGkOIApA \n\
    - Notre compte Twitter : twitter.com/42AI_ \n\
    - Notre compte Linkedin : www.linkedin.com/company/42-artificial-intelligence/\n\
\n\
Pour toutes questions spécifiques, nos *membres du CA* sont là pour toi ! :\n\
    - *Président* : Amric Trudel (@atrudel)\n\
    - *Vice Président* : Maxime Choulika (@cmaxime)\n\
    - *Trésorier - Community Manager* : Guillaume Ozserttas (@gozsertt)\n\
    - *Secrétaire - Partenariats* : Myriam Benzarti (@mybenzar)"


        