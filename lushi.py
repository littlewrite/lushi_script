# -*- coding: utf-8 -*-
import logging

import pyautogui
import cv2
import time
import numpy as np
import argparse
import os
import yaml
import datetime
from PIL import Image
from types import SimpleNamespace

from utils.log_util import LogUtil
from utils.util import find_lushi_window, find_icon_location, restart_game, tuple_add, find_relative_loc, screenshot
from utils.images import get_sub_np_array
from utils.battle_ai import BattleAi
import utils.logging_util

logger = logging.getLogger()


class Agent:
    def __init__(self, cfg):
        self.is_screenshot = cfg.get('is_screenshot') or False
        if cfg['lang'].startswith('EN'):
            self.lang = 'eng'
            self.loc_file = 'config/locs_eng.yaml'
            self.img_folder = 'resource/imgs_eng_1024x768'
            self.title = 'hearthstone'
        elif cfg['lang'].startswith('ZH'):
            self.lang = 'chs'
            self.loc_file = 'config/locs_chs.yaml'
            self.img_folder = "resource/imgs_chs_1600x900"
            self.title = "炉石传说"
        else:
            raise ValueError(f"Language {cfg['lang']} is not supported yet")

        self.debug = False  # TODO check before commit 
        self.icons = {}
        self.treasure_blacklist = {}
        self.heros_whitelist = {}
        self.heros_blacklist = {}
        self.game = None
        self.skill_seq_cache = {}
        self.start_seq = {}
        self.side = None
        self.surprise_in_mid = False
        self.states = ['box', 'mercenaries', 'team_lock', 'travel', 'boss_list', 'team_list', 'map_not_ready',
                       'goto', 'show', 'teleport', 'start_game', 'member_not_ready', 'not_ready_dots', 'battle_ready',
                       'treasure_list', 'treasure_replace', 'destroy', 'blue_portal', 'boom', 'visitor_list',
                       'final_reward', 'final_reward2', 'final_confirm', 'close', 'ok']

        self.load_config(cfg)
        self.log_util = LogUtil(self.basic.hs_log)

    def read_sub_imgs(self, sub):
        imgs = [img for img in os.listdir(os.path.join(self.img_folder, sub)) if img.endswith('.png')]
        for img in imgs:
            k = img.split('.')[0]
            v = cv2.cvtColor(cv2.imread(os.path.join(self.img_folder, sub, img)), cv2.COLOR_BGR2GRAY)
            x = getattr(self, sub)
            x[k] = v

    def load_config(self, cfg):
        with open(self.loc_file, 'r', encoding='utf-8') as f:
            loc_cfg = yaml.safe_load(f)

        self.locs = SimpleNamespace(**loc_cfg['location'])
        for sub in ['icons', 'treasure_blacklist', 'heros_whitelist', 'heros_blacklist']:
            self.read_sub_imgs(sub)

        hero_info = cfg['hero']
        self.heros = {}
        for k, v in hero_info.items():
            spell_order = [int(x) - 1 for x in v[2].split(',')]
            self.heros[k] = [v[0], v[1], spell_order, v[3]]
            self.skill_seq_cache[k] = v[-2]
        del cfg['hero']
        cfg['hs_log'] = os.path.join(os.path.dirname(cfg['hs_path']), 'Logs', 'Power.log')
        self.basic = SimpleNamespace(**cfg)
        pyautogui.PAUSE = self.basic.delay

    def check_in_screen(self, name, prefix='icons'):

        rect, screen = find_lushi_window(self.title)
        try:
            icon = getattr(self, prefix)[name]
        except:
            return False, None, None
        success, X, Y, conf = find_icon_location(screen, icon, self.basic.confidence)
        del screen
        loc = X, Y
        return success, loc, rect
    
    # 传入图片，匹配子图
    def find_in_image(self, screen, name, prefix='icons'):
        try:
            icon = getattr(self, prefix)[name]
        except:
            return False, None, None
        success, X, Y, conf = find_icon_location(screen, icon, self.basic.confidence)
        del screen
        loc = X, Y
        return success, loc

    def scan_surprise_loc(self, rect):
        # time.sleep(5)
        logger.info('Scanning surprise')
        pyautogui.moveTo(tuple_add(rect, self.locs.scroll))
        tic = time.time()
        while True:
            success, loc, rect = self.check_in_screen('surprise')
            if success:
                logger.info(f"Found surprise at start {loc}")
                return loc
            if self.check_in_screen('start_point')[0]:
                break
            if time.time() - tic > 10:
                return

        for _ in range(10):
            pyautogui.scroll(60)
            success, loc, rect = self.check_in_screen('surprise')
            if success:
                for _ in range(10):
                    pyautogui.scroll(-60)
                logger.info(f"Found surprise during scrolling {loc}")
                return loc

        logger.info("Did not found any surprise")
        return None

    def task_submit(self, rect):
        if self.basic.auto_tasks and self.lang == "chs":
            # time.sleep(5)
            # select Camp Fire
            pyautogui.click(tuple_add(rect, (641, 669)))
            pyautogui.click(tuple_add(rect, (1302, 744)))

            # first task
            pyautogui.click(tuple_add(rect, (588, 329)))
            pyautogui.click(tuple_add(rect, (548, 719)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (1438, 440)))

            # second task
            pyautogui.click(tuple_add(rect, (988, 336)))
            pyautogui.click(tuple_add(rect, (548, 719)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (1438, 440)))

            # third task
            pyautogui.click(tuple_add(rect, (602, 474)))
            pyautogui.click(tuple_add(rect, (548, 719)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (1438, 440)))

            # forth task
            pyautogui.click(tuple_add(rect, (988, 474)))
            pyautogui.click(tuple_add(rect, (548, 719)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (928, 544)))
            pyautogui.click(tuple_add(rect, (1438, 440)))

            # exit the campfire
            pyautogui.click(tuple_add(rect, (1438, 440)))
            # select first first boss of map
            pyautogui.click(tuple_add(rect, (654, 431)))

    def start_battle(self):

        logger.info("Scanning battlefield")

        rect, screen = find_lushi_window(self.title)

        del self.log_util
        self.log_util = LogUtil(self.basic.hs_log)
        game = self.log_util.parse_game()

        first_x, mid_x, last_x, y = self.locs.heros
        n_my_hero = len(game.my_hero)
        is_even = n_my_hero % 2 == 0
        for i in range(n_my_hero):
            if is_even:
                x_offset = (mid_x - first_x) * (- 0.5 - n_my_hero // 2 + i + 1)
            else:
                x_offset = (mid_x - first_x) * (0 - n_my_hero // 2 + i)
            game.my_hero[i].set_pos(mid_x + x_offset + rect[0], y + rect[1])

        first_x, mid_x, last_x, y = self.locs.enemies
        n_enemy_hero = len(game.enemy_hero)
        for i in range(n_enemy_hero):
            if n_enemy_hero % 2 == 0:
                x_offset = (mid_x - first_x) * (- 0.5 - n_enemy_hero // 2 + i + 1)
            else:
                x_offset = (mid_x - first_x) * (0 - n_enemy_hero // 2 + i)
            game.enemy_hero[i].set_pos(mid_x + x_offset + rect[0], y + rect[1])

        strategy = BattleAi.battle(game.my_hero, game.enemy_hero)
        pyautogui.click(tuple_add(rect, self.locs.empty))

        for hero_i, h in enumerate(game.my_hero):
            if h.lettuce_has_manually_selected_ability:
                continue

            pyautogui.click(h.pos)
            card_id = h.card_id[:-3]
            if card_id not in self.heros:
                skill_loc = tuple_add(rect, (self.locs.skills[0], self.locs.skills[-1]))
            else:
                skill_loc = None
                skill_seq = self.heros[card_id][-2]
                for skill_id in skill_seq:
                    skill_cooldown_round = h.spell[skill_id].lettuce_current_cooldown
                    if skill_cooldown_round == 0:
                        skill_loc = tuple_add(rect, (self.locs.skills[skill_id], self.locs.skills[-1]))
                        break
            pyautogui.click(skill_loc)
            enemy_id = strategy[hero_i]
            pyautogui.click(game.enemy_hero[enemy_id].pos)
            pyautogui.click(tuple_add(rect, self.locs.empty))

    def select_members(self):
        game = self.log_util.parse_game()
        rect, screen = find_lushi_window(self.title, to_gray=False)
        del screen
        hero_in_battle = [h for h in game.my_hero if h.card_id[:-3] in self.heros]
        if len(hero_in_battle) < 3:
            current_seq = {h.card_id[:-3]: i for i, h in enumerate(game.setaside_hero)}
            heros_sorted = {k: v[-1] for k, v in sorted(
                self.heros.items(), key=lambda item: item[1][-1])}
            card_id_seq = list(heros_sorted.keys())
            card_id_seq = [x for x in card_id_seq if x in current_seq]

            for i in range(3 - len(hero_in_battle)):
                if len(card_id_seq) > 0:

                    cards_in_hand = len(card_id_seq)
                    card_id = card_id_seq.pop(0)

                    first_x, last_x, y = self.locs.members
                    mid_x = (first_x + last_x) // 2
                    current_pos = current_seq[card_id]

                    if cards_in_hand > 3:
                        dis = (last_x - first_x) // (cards_in_hand - 1)
                        loc = (first_x + dis * current_pos, y)
                    elif cards_in_hand == 3:
                        loc = (mid_x + self.locs.members_distance * (current_pos - 1), y)
                    elif cards_in_hand == 2:
                        if current_pos == 0:
                            factor = -1
                        elif current_pos == 1:
                            factor = 1
                        else:
                            raise ValueError("Not possible")

                        loc = (mid_x + self.locs.members_distance // 2 * factor, y)
                    elif cards_in_hand == 1:
                        loc = (mid_x, y)
                    else:
                        raise ValueError("Not possible")

                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.moveTo(tuple_add(rect, self.locs.dragto))
                    pyautogui.click()

                    del current_seq[card_id]
                    for k, v in current_seq.items():
                        if v > current_pos:
                            current_seq[k] = v - 1

    def screen_record(self, prefix):
        timeFormated = datetime.datetime.now().strftime("%Y-%m-%d_%H-%M")
        imageName = f"{prefix}_{timeFormated}.png"
        _, screen = find_lushi_window(self.title, to_gray=False)

        isinstance(screen, np.ndarray)
        len(screen.shape) == 3
        screen.shape[2] == 3
        img = Image.fromarray(screen, 'RGB')
        img.save(imageName)
    
    # 从按照黑名单剔除宝藏，返回可选项，如果没有则返回[1], 最多返回：[1,2,3]
    def pick_treasure(self, screen):
        advice_idx = []
        not_advice_idx = []
        for key in self.treasure_blacklist.keys():
            for idx in range(1, 4):
                loc = self.locs.treasures_locaion[idx]
                oneTrasure = get_sub_np_array(screen, loc[0], loc[1], loc[2], loc[3])
                success, X, Y, conf = find_icon_location(oneTrasure, self.treasure_blacklist[key], self.basic.confidence)
                if success :
                    not_advice_idx.append(idx)

        if 2 < len(not_advice_idx):
            return [1]
        else :
            for idx in range(1, 4):
                if idx not in not_advice_idx:
                    advice_idx.append(idx)
            return advice_idx

    # 按照黑白名单选择神秘人选项，白名单命中，则选白名单的。黑名单命中这不选，如果白名单没命中，黑名单全命中，则随机选
    def pick_visitor(self, screen, rect):
        is_in_whitelist = False
        is_in_blacklist = False
        idx_whiteList = []
        for key in self.heros_whitelist.keys():
            success, loc = self.find_in_image(screen, key, prefix='heros_whitelist')
            if success:
                is_in_whitelist = True
                for idx, vloc in self.locs.visitors:
                    if vloc[0] < loc[0] and loc[1] < vloc[2]:
                        idx_whiteList.append(idx)

        if is_in_whitelist:
            visitor_id = np.random.randint(0, 3)
            visitor_loc = (self.locs.visitors[visitor_id], self.locs.visitors[-1])
            pyautogui.click(tuple_add(rect, visitor_loc))

        for key in self.heros_blacklist.keys():
            success, loc = self.find_in_image(screen, key, prefix='heros_blacklist')
            if success:
                is_in_blacklist = True
                return loc

        if not is_in_whitelist:
            visitor_id = np.random.randint(0, 3)
            visitor_loc = (self.locs.visitors[visitor_id], self.locs.visitors[-1])
            pyautogui.click(tuple_add(rect, visitor_loc))

        pyautogui.click(tuple_add(rect, self.locs.visitors_confirm))

    def state_handler(self, state, tic, text):
        success, loc, rect = self.check_in_screen(text)
        '''
        self.states = ['box', 'mercenaries', 'team_lock', 'travel', 'boss_list', 'team_list', 'map_not_ready',
                  'goto', 'show', 'teleport', 'start_game', 'member_not_ready', 'not_ready_dots', 'battle_ready',
                  'treasure_list', 'treasure_replace', 'destroy', 'blue_portal', 'boom', 'visitor_list',
                  'final_reward', 'final_reward2', 'final_confirm', 'ok', 'close']
        '''
        if success:
            if state != text:
                state = text
                tic = time.time()

            if state in ['mercenaries', 'box', 'team_lock', 'close', 'ok']:
                pyautogui.click(tuple_add(rect, loc))
                logger.info(f'clicked {state}')

            if state == 'travel':
                pyautogui.click(tuple_add(rect, loc))
                pyautogui.click(tuple_add(rect, self.locs.travel))

            if state == 'boss_list':
                if self.basic.boss_id > 5:
                    id_standard = (self.basic.boss_id - 6) * 2
                    x_id = id_standard % 3
                    y_id = id_standard // 3
                    loc = (self.locs.boss[x_id], self.locs.boss[3 + y_id])
                    if self.lang == "chs":
                        loc_page_right = (1091, 479)
                    if self.lang == "eng":
                        loc_page_right = (765.418)
                    pyautogui.click(tuple_add(rect, loc_page_right))
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))
                else:
                    x_id = self.basic.boss_id % 3
                    y_id = self.basic.boss_id // 3
                    loc = (self.locs.boss[x_id], self.locs.boss[3 + y_id])
                    pyautogui.click(tuple_add(rect, loc))
                    pyautogui.click(tuple_add(rect, self.locs.start_game))

            if state == 'team_list':
                x_id = self.basic.team_id % 3
                y_id = self.basic.team_id // 3

                pyautogui.click(tuple_add(rect, (self.locs.teams[x_id], self.locs.teams[3 + y_id])))
                pyautogui.click(tuple_add(rect, self.locs.team_select))
                pyautogui.click(tuple_add(rect, self.locs.team_lock))
                time.sleep(7)  # avoid too low speed of entering map action to skip task_submit and scan_surprise
                self.task_submit(rect)
                # if self.basic.boss_id != 0:
                surprise_loc = self.scan_surprise_loc(rect)

                if surprise_loc is not None:
                    if surprise_loc[0] < self.locs.start_point[0]:
                        self.side = 'left'
                    else:
                        self.side = 'right'
                    first_x, mid_x, last_x, y = self.locs.focus
                    if np.abs(surprise_loc[0] - mid_x) < 100:
                        self.surprise_in_mid = True
                    else:
                        self.surprise_in_mid = False
                    logger.info(f'Surprise side {self.side}, surprise in middile {self.surprise_in_mid}')

            if state == 'map_not_ready':
                first_x, mid_x, last_x, y = self.locs.focus
                if self.side is None:
                    self.side = 'left'
                if self.side == 'left':
                    if self.surprise_in_mid:
                        x1, x2, x3 = first_x, (first_x + mid_x) // 2, mid_x
                    else:
                        x1, x2, x3 = mid_x, (first_x + mid_x) // 2, first_x                 
                else:
                    if self.surprise_in_mid:
                        x1, x2, x3 = last_x, (last_x + mid_x) // 2, mid_x
                    else:
                        x1, x2, x3 = mid_x, (last_x + mid_x) // 2, last_x

                for x in (x1, x2, x3):
                    pyautogui.moveTo(tuple_add(rect, (x, y)))
                    pyautogui.mouseDown()
                    pyautogui.mouseUp()

            if state in ['goto', 'show', 'teleport', 'start_game']:
                pyautogui.click(tuple_add(rect, self.locs.start_game))

            if state == 'member_not_ready':
                logger.info(f" member_not_ready  during scrolling ")
                self.select_members()

            if state == 'not_ready_dots':
                logger.info(f" not_ready_dots  during scrolling lo ")
                self.start_battle()

            if state == 'battle_ready':
                logger.info(f" battle_ready  during scrolling lo ")
                pyautogui.click(tuple_add(rect, self.locs.start_battle))

            if state in ['treasure_list', 'treasure_replace']:
                _, screen = find_lushi_window(self.title)
                adive = self.pick_treasure(screen)
                while True:
                    id = np.random.randint(1, 3)
                    if id in adive:
                        treasure_loc = (self.locs.treasures[id], self.locs.treasures[-1])
                        break
                
                print(f"click treasure : {rect}, {treasure_loc}")
                pyautogui.click(tuple_add(rect, treasure_loc))
                # hero treasure screenshot before confirm
                if self.



 :
                    self.screen_record(state)
                pyautogui.click(tuple_add(rect, self.locs.treasures_collect))
                del screen

            if state in ['destroy', 'blue_portal', 'boom']:
                if self.basic.early_stop:
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))
                else:
                    pyautogui.click(tuple_add(rect, self.locs.start_game))

            if state == 'visitor_list':
                _, screen = find_lushi_window(self.title)
                # advice = self.pick_visitor(screen, rect) # TODO test
                is_in_whitelilst = False
                for key in self.heros_whitelist.keys():
                    success, loc, rect = self.check_in_screen(key, prefix='heros_whitelist')
                    if success:
                        is_in_whitelilst = True
                        pyautogui.click(tuple_add(rect, loc))
                        break

                if not is_in_whitelilst:
                    visitor_id = np.random.randint(0, 3)
                    visitor_loc = (self.locs.visitors[visitor_id], self.locs.visitors[-1])
                    pyautogui.click(tuple_add(rect, visitor_loc))

                # visitor, pick mission record
                if self.debug:
                    self.screen_record(state)
                if self.is_screenshot:
                    screenshot(self.title)

                pyautogui.click(tuple_add(rect, self.locs.visitors_confirm))

                for _ in range(4):
                    pyautogui.click(tuple_add(rect, self.locs.empty))

                logger.info("Visitors Selected")
                if self.basic.early_stop:
                    logger.info("Early stopping")
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))

            if state in ['final_reward', 'final_reward2']:
                reward_locs = eval(self.locs.rewards["all"])    # click all of 3， 4， 5 rewards location
                for loc in reward_locs:
                    pyautogui.moveTo(tuple_add(rect, loc))
                    pyautogui.click()

                if self.basic.screenshot_reward or self.debug : # record reward by image
                    self.screen_record(state)

                pyautogui.moveTo(tuple_add(rect, self.locs.rewards['confirm']))
                pyautogui.click()

            if state == 'final_confirm':
                pyautogui.click(tuple_add(rect, self.locs.final_confirm))

        return success, tic, state, rect

    def run(self):
        if self.basic.auto_restart:
            while True:
                try:
                    self.run_pve()
                except Exception as e:
                    logger.error(f'错误：{e}')
                    if self.is_screenshot:
                        screenshot(self.title)
                    restart_game(self.lang, self.basic.bn_path, False)
        else:
            self.run_pve()

    def run_pve(self):
        time.sleep(2)
        success, loc, rect = self.check_in_screen('mercenaries')

        side = None
        surprise_in_mid = False
        tic = time.time()
        state = ""

        while True:
            currentTime = time.strftime("%Y-%m-%d %H:%M:%S", time.localtime())
            pyautogui.click(tuple_add(rect, self.locs.empty))
            if time.time() - tic > self.basic.longest_waiting:
                if self.is_screenshot:
                    screenshot(self.title)
                if state == 'not_ready_dots' or state == 'member_not_ready':
                    pyautogui.click(tuple_add(rect, self.locs.options))
                    pyautogui.click(tuple_add(rect, self.locs.surrender))
                elif state == 'map_not_ready':
                    pyautogui.click(tuple_add(rect, self.locs.view_team))
                    pyautogui.click(tuple_add(rect, self.locs.give_up))
                    pyautogui.click(tuple_add(rect, self.locs.give_up_cfm))
                else:
                    restart_game(self.lang, self.basic.bn_path)
                tic = time.time()
            else:
                logger.info(
                    f"[{currentTime}] Last state {state}, time taken: {time.time() - tic}, side: {side}, surprise_in_mid: {surprise_in_mid}")

            for state_text in self.states:
                success, tic, state, rect = self.state_handler(state, tic, state_text)
                if success:
                    pyautogui.click(tuple_add(rect, self.locs.empty))


def run_from_gui(cfg):
    logger.debug(cfg)
    if cfg['lang'].startswith('EN'):
        lang = 'eng'
    elif cfg['lang'].startswith('ZH'):
        lang = 'chs'
    else:
        lang = None
    restart_game(lang, cfg['bn_path'], kill_existing=False)
    agent = Agent(cfg=cfg)
    agent.run()


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--lang', choices=['chs', 'eng'], default='chs', help='Choose Your Hearthstone Language')
    parser.add_argument('--config', default='config/default.yaml', help='launch config filename')
    parser.add_argument('--func', choices=['run', 'coor'], help='Run main function or find coordinates')
    args = parser.parse_args()

    if args.func == 'run':
        with open(args.config, 'r', encoding='utf-8') as f:
            cfg = yaml.safe_load(f)

        if args.lang == 'chs':
            cfg['lang'] = 'ZH-1600x900'
        else:
            cfg['lang'] = 'EN-1024x768'

        run_from_gui(cfg)
    elif args.func == 'coor':
        if args.lang == 'chs':
            title = '炉石传说'
        elif args.lang == 'eng':
            title = 'Hearthstone'
        else:
            title = None
        while True:
            find_relative_loc(title)
            time.sleep(1)


if __name__ == '__main__':
    main()
