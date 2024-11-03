import json
import time
from os import close
import random

from src import util
from src.game import DisplayEntity, Player, Level, Bear, Menu, MenuInterface, TextBox, Entity, HoneyJar, HoneySpill, \
    ProgressBar, level_array, saves_array, Save
from src.geometry import line_length
from src.util import Message
from enum import Enum, auto

UP = "Up"
DOWN = "Down"
LEFT = "Left"
RIGHT = "Right"

TIMESTEP = 1 / 100

BEAR_EAT_TIME = 10
PLAYER_STEAL_TIME = 4

class GameState(Enum):
    MAIN_MENU = auto()
    GAME_SELECT = auto()
    OPTIONS_SELECT = auto()
    TUTORIAL_SELECT = auto()
    TUTORIAL_VIEW = auto()
    MENU = auto()
    GAME = auto()
    SWITCH_LEVEL = auto()
    SWITCH_LEVEL_FINALISE = auto()
    RESULT = auto()

def create_entity(entity_cls, entity_list, output_pipe, *args, visible=True):
    entity = entity_cls(*args)
    entity_list.append(entity)
    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE, visible, str(entity))
    send_message(output_pipe, Message.ENTITY_CREATED, display_entity)
    return entity

def create_entity_string(entity_string, entity_list, output_pipe, *args, visible=True):
    entity = Entity.from_string(entity_string, *args)
    entity_cls = entity.__class__
    entity_list.append(entity)
    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE, visible, str(entity))
    send_message(output_pipe, Message.ENTITY_CREATED, display_entity)
    return entity

def get_by_id(object_id, object_list):
    for object_ in object_list:
        if object_.get_id() == object_id:
            return object_
    return None

def show_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, True))

def hide_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, False))

def kill_entity(entity_id, entity_list, output_pipe):
    for entity in entity_list:
        if entity.get_id() == entity_id:
            entity_list.remove(entity)
            break
    send_message(output_pipe, Message.ENTITY_KILL, entity_id)

def create_menu(menu_list, output_pipe, *args, **kwargs):
    menu = Menu(*args, **kwargs)
    menu_size = menu.get_num_items()
    menu_index = menu.get_active_index()
    menu_id = menu.get_id()
    menu_interface = MenuInterface(menu_size, menu_index, menu_id)
    menu_list.append(menu_interface)
    send_message(output_pipe, Message.MENU_CREATED, menu)
    return menu_id

def create_menu_from_file(menu_list, output_pipe, *args, **kwargs):
    menu = Menu.from_file(*args, **kwargs)
    menu_size = menu.get_num_items()
    menu_index = menu.get_active_index()
    menu_id = menu.get_id()
    menu_interface = MenuInterface(menu_size, menu_index, menu_id)
    menu_list.append(menu_interface)
    send_message(output_pipe, Message.MENU_CREATED, menu)
    return menu_id

def add_item_to_menu(menu_id, menu_list, menu_item, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    menu_interface.num_items += 1
    send_message(output_pipe, Message.MENU_ADD_ITEM, (menu_id, menu_item))

def remove_item_from_menu(menu_id, menu_list, menu_index, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    menu_interface.num_items -= 1
    if menu_interface.active_index >= menu_interface.num_items:
        menu_interface.active_index -= 1
        send_message(output_pipe, Message.MENU_CHANGE_INDEX, (menu_id, menu_interface.active_index))
    send_message(output_pipe, Message.MENU_REMOVE_ITEM, (menu_id, menu_index))

def set_active_index_menu(menu_id, menu_list, menu_index, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    if menu_index < menu_interface.num_items:
        menu_interface.active_index = menu_index
        send_message(output_pipe, Message.MENU_CHANGE_INDEX, (menu_id, menu_index))

def handle_menu_inputs(menu_id, menu_list, inputs, output_pipe):
    menu = get_by_id(menu_id, menu_list)
    if inputs[UP]:
        if menu.active_index > 0:
            set_active_index_menu(menu_id, menu_list, menu.active_index - 1, output_pipe)
        return True
    if inputs[DOWN]:
        if menu.active_index < menu.num_items - 1:
            set_active_index_menu(menu_id, menu_list, menu.active_index + 1, output_pipe)
        return True
    return False

def show_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, True))

def hide_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, False))

def set_menu_formatting(menu_id, format_index, formatting, output_pipe):
    send_message(output_pipe, Message.MENU_SET_FORMATTING, (menu_id, format_index, formatting))

def create_text_box(text_box_list, output_pipe, *args, **kwargs):
    text_box = TextBox(*args, **kwargs)
    text_box_id = text_box.get_id()
    send_message(output_pipe, Message.TEXT_BOX_CREATED, text_box)
    text_box_list.append(text_box_id)
    return text_box_id

def show_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, True))

def hide_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, False))

def hide_all_text_boxes(text_box_list, output_pipe):
    for text_box in text_box_list:
        hide_text_box(text_box, output_pipe)

def delete_text_box(text_box_id, text_box_list, output_pipe):
    text_box_list.remove(text_box_id)
    send_message(output_pipe, Message.TEXT_BOX_DELETED, text_box_id)

def show_all_entities(entity_list, output_pipe):
    for entity in entity_list:
        show_entity(entity.get_id(), output_pipe)

def hide_all_entities(entity_list, output_pipe):
    for entity in entity_list:
        hide_entity(entity.get_id(), output_pipe)

def create_progress_bar(progress_bar_list, output_pipe, *args, **kwargs):
    progress_bar = ProgressBar(*args, **kwargs)
    progress_bar_id = progress_bar.get_id()
    send_message(output_pipe, Message.PROGRESS_BAR_CREATED, progress_bar)
    progress_bar_list.append(progress_bar_id)
    return progress_bar_id

def update_progress_bar(progress_bar_id, position, progress, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_UPDATE, (progress_bar_id, position, progress))

def show_progress_bar(progress_bar_id, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_VISIBLE, (progress_bar_id, True))

def hide_progress_bar(progress_bar_id, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_VISIBLE, (progress_bar_id, False))

def hide_all_progress_bars(progress_bar_list, output_pipe):
    for progress_bar in progress_bar_list:
        hide_progress_bar(progress_bar, output_pipe)

def show_information(output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", True))

def hide_information(output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", False))

def update_information(time_remaining, collected_gold, output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("TIME_REMAINING", time_remaining))
    send_message(output_pipe, Message.UPDATE_SETTING, ("COLLECTED_GOLD", collected_gold))

def kill_level_entities(entity_list, level_entity_list, output_pipe):
    for entity_id in level_entity_list:
        kill_entity(entity_id, entity_list, output_pipe)

def spawn_level_entities(level, entity_list, level_entity_list, output_pipe):
    for entity_type, position in level.iter_entities():
        entity = create_entity_string(entity_type, entity_list, output_pipe, position, 0, visible=True)
        level_entity_list.append(entity.get_id())

def create_save(saves, save_name):
    save = Save(save_name, 0, 0)
    saves.append(save)
    return save

def add_save_to_menu(save, menu_id, menu_list, output_pipe):
    add_item_to_menu(menu_id, menu_list, (save.get_save_name(), None), output_pipe)

def recv_message(input_pipe):
    return input_pipe.recv()

def send_message(output_pipe, message, value):
    output_pipe.send((message, value))

def hide_all(text_box_list, progress_bar_list, menu_list, output_pipe):
    hide_all_text_boxes(text_box_list, output_pipe)
    hide_all_progress_bars(progress_bar_list, output_pipe)
    for menu in menu_list:
        hide_menu(menu.get_id(), output_pipe)

def create_result_text_box(text_box_list, current_save, output_pipe):
    if current_save.get_condition() == Save.WON:
        return create_text_box(text_box_list, output_pipe,
                        "CONGRATULATIONS",
                        f"You survived, and stole {current_save.get_collected_gold()} gold from the bear! Press ENTER to return to the main menu")
    elif current_save.get_condition() == Save.LOST:
        return create_text_box(text_box_list, output_pipe,
                        "DISAPPOINTING...",
                        f"You lost the game. California state recovered what remained of your body. Press ENTER to return to the main menu")

def game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe):
    hide_all(text_box_list, progress_bar_list, menu_list, output_pipe)
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", False))
    if current_save is not None:
        current_save.save("saves")
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.MAIN_MENU)
    return GameState.MAIN_MENU

def game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe):
    hide_all(text_box_list, progress_bar_list, menu_list, output_pipe)
    show_text_box(result_text_box, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.RESULT)
    return GameState.RESULT

def game_state_game_select(games_menu_id, output_pipe):
    show_menu(games_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.GAME_SELECT)
    return GameState.GAME_SELECT

def game_state_options_select(options_menu_id, output_pipe):
    show_menu(options_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.OPTIONS_SELECT)
    return GameState.OPTIONS_SELECT

def game_state_tutorial_select(games_menu_id, tutorial_question_id, save_warning_id, output_pipe):
    hide_menu(games_menu_id, output_pipe)
    hide_text_box(save_warning_id, output_pipe)
    show_text_box(tutorial_question_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.TUTORIAL_SELECT)
    return GameState.TUTORIAL_SELECT

def game_state_tutorial_view(tutorial_question_id, tutorial_menu_id, output_pipe):
    hide_text_box(tutorial_question_id, output_pipe)
    show_menu(tutorial_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.TUTORIAL_VIEW)
    return GameState.TUTORIAL_VIEW

def game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe):
    hide_text_box(switch_level_warning, output_pipe)
    hide_text_box(tutorial_question_id, output_pipe)
    hide_menu(games_menu_id, output_pipe)
    hide_menu(tutorial_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.GAME)
    show_all_entities(entity_list, output_pipe)
    return GameState.GAME

def game_state_switch_level(switch_level_warning, output_pipe):
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.SWITCH_LEVEL)
    show_text_box(switch_level_warning, output_pipe)
    return GameState.SWITCH_LEVEL

def is_command_yes(command):
    return len(command) > 0 and command[0].upper() == "Y"

def load_options():
    filepath = util.abspath("res/options.json")
    with open(filepath, "r") as file:
        options = json.load(file)
    return options

def save_options(options):
    filepath = util.abspath("res/options.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(options, file, ensure_ascii=False)

def physics_thread(input_pipe, output_pipe):
    timestep = TIMESTEP
    prev_time = time.perf_counter()

    entity_list = []
    level_entity_list = []
    menu_list = []
    text_box_list = []
    progress_bar_list = []

    inputs = {
        UP:    False,
        DOWN:  False,
        LEFT:  False,
        RIGHT: False
    }
    options = load_options()

    options_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/options.json", visible=False)
    options_invalid_id = create_text_box(text_box_list, output_pipe,
                                         "ERROR", "Invalid input.", visible=False)
    options_invalid_time = 3

    count = 1
    for key, value in options.items():
        send_message(output_pipe, Message.UPDATE_SETTING, (key, value))
        set_menu_formatting(options_menu_id, count, (value,), output_pipe)
        count += 1

    command = None
    input_cooldown = 0.2
    input_time = time.perf_counter()
    levels = level_array("res/levels")
    num_levels = len(levels)
    level_index = 0
    level = levels[level_index]
    level_duration = 0
    game_state = GameState.MAIN_MENU
    main_menu_selector = 0
    send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
    send_message(output_pipe, Message.LEVEL_CHANGED, level)
    player = create_entity(Player, entity_list, output_pipe, (0, 0), 0, visible=False)
    player_progress_bar_id = create_progress_bar(progress_bar_list, output_pipe, player.get_position(), 0.1, visible=False)
    held_entity = None
    player_steal = False
    player_steal_time = 0
    player_steal_info_time = 3
    player_gold = 0
    bear = create_entity(Bear, entity_list, output_pipe, (-5, -5), 0, visible=False)
    bear_progress_bar_id = create_progress_bar(progress_bar_list, output_pipe, bear.get_position(), 0.1, visible=False)
    bear_target = None
    bear_eating_time = 0
    bear_eating = False
    bear_spawned = False

    tutorial_question_id = create_text_box(text_box_list, output_pipe,
                                           "READ TUTORIAL", "Would you like to read the tutorial?\n\nEnter yes/no into the console",
                                           visible=False)
    tutorial_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/tutorial.json", visible=False)
    help_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/help.json", visible=False)

    bear_30s_warning = create_text_box(text_box_list, output_pipe,"INFORMATION", "The Bear is arriving in 30 seconds!", visible=False)
    bear_0s_warning = create_text_box(text_box_list, output_pipe,"INFORMATION", "The Bear has arrived!", visible=False)
    player_steal_info = create_text_box(text_box_list, output_pipe,"INFORMATION", "You stole some gold!", visible=False)

    spawn_level_entities(level, entity_list, level_entity_list, output_pipe)

    games_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/select_game.json", visible=False)

    switch_level_warning = create_text_box(text_box_list, output_pipe,
                                           "WARNING", "Are you sure you want to progress to the next level? Enter yes/no into the console",
                                           visible=False)

    result_text_box = -1

    save_warning_time = 3
    save_warning_id = create_text_box(text_box_list, output_pipe, "ERROR", "Cannot create a save file without a name!", visible=False)
    saves_list = saves_array("saves")
    current_save = None

    for save in saves_list:
        add_save_to_menu(save, games_menu_id, menu_list, output_pipe)

    running = True
    paused  = False
    display_help = False
    while running:
        while input_pipe.poll():
            message, data = recv_message(input_pipe)
            if message == Message.EXIT:
                running = False
            if message == Message.TIMESTEP:
                timestep = data
            if message == Message.KEY_PRESS:
                if data in inputs.keys():
                    inputs[data] = True
            if message == Message.KEY_RELEASE:
                if data in inputs.keys():
                    inputs[data] = False
            if message == Message.COMMAND:
                command = data
            if message == Message.INPUT_BEGIN:
                paused = True
            if message == Message.INPUT_END:
                paused = False

        curr_time = time.perf_counter()
        delta = curr_time - prev_time
        if delta < timestep:
            continue
        prev_time = curr_time

        if game_state == GameState.MAIN_MENU:
            if curr_time - input_time > input_cooldown:
                if inputs[UP]:
                    if main_menu_selector > 0:
                        main_menu_selector -= 1
                    send_message(output_pipe, Message.UPDATE_SETTING, ("MAIN_MENU_SELECTOR", main_menu_selector))
                    input_time = curr_time
                if inputs[DOWN]:
                    if main_menu_selector < 2:
                        main_menu_selector += 1
                    send_message(output_pipe, Message.UPDATE_SETTING, ("MAIN_MENU_SELECTOR", main_menu_selector))
                    input_time = curr_time
                if command is not None:
                    if main_menu_selector == 0:
                        game_state = game_state_game_select(games_menu_id, output_pipe)
                    elif main_menu_selector == 1:
                        game_state = game_state_options_select(options_menu_id, output_pipe)
                    elif main_menu_selector == 2:
                        send_message(output_pipe, Message.EXIT, 0)
                    command = None

        if game_state == GameState.GAME_SELECT:
            save_warning_time += delta
            if save_warning_time < 3:
                show_text_box(save_warning_id, output_pipe)
            else:
                hide_text_box(save_warning_id, output_pipe)
            games_menu = get_by_id(games_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(games_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if games_menu.active_index == 0:
                        hide_menu(games_menu_id, output_pipe)
                        game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                    elif games_menu.active_index == 1:
                        if command != "":
                            current_save = create_save(saves_list, command)
                            add_save_to_menu(current_save, games_menu_id, menu_list, output_pipe)
                            current_save.save("saves")
                            save_warning_time = 3
                            game_state = game_state_tutorial_select(games_menu_id, tutorial_question_id, save_warning_id, output_pipe)
                        else:
                            save_warning_time = 0
                    else:
                        if command.upper() == "DELETE":
                            delete_index = games_menu.active_index - 2
                            delete_save = saves_list[delete_index]
                            delete_save.delete("saves")
                            current_save = None
                            saves_list.pop(delete_index)
                            remove_item_from_menu(games_menu_id, menu_list, games_menu.active_index, output_pipe)
                        else:
                            current_save = saves_list[games_menu.active_index - 2]
                            player_gold = current_save.get_collected_gold()
                            level_index = current_save.get_level_index()
                            if current_save.get_condition() != Save.PLAYING:
                                result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                                game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)
                            else:
                                game_state = GameState.SWITCH_LEVEL_FINALISE
                    command = None

        if game_state == GameState.TUTORIAL_SELECT:
            if command is not None:
                if is_command_yes(command):
                    game_state = game_state_tutorial_view(tutorial_question_id, tutorial_menu_id, output_pipe)
                else:
                    game_state = game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe)
                command = None

        if game_state == GameState.TUTORIAL_VIEW:
            tutorial_menu = get_by_id(tutorial_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(tutorial_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if tutorial_menu.active_index == 0:
                        game_state = game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe)

        if game_state == GameState.OPTIONS_SELECT:
            options_invalid_time += delta
            if options_invalid_time < 3:
                show_text_box(options_invalid_id, output_pipe)
            else:
                hide_text_box(options_invalid_id, output_pipe)
            options_menu = get_by_id(options_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(options_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if options_menu.active_index == 0:
                        hide_menu(options_menu_id, output_pipe)
                        game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                        options_invalid_time = 3
                    if options_menu.active_index == 1:
                        if command.upper() == "TRUE":
                            setting = True
                        elif command.upper() == "FALSE":
                            setting = False
                        else:
                            setting = None

                        if setting is None:
                            options_invalid_time = 0
                        else:
                            options["DISPLAY_FPS"] = setting
                            send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_FPS", setting))
                            set_menu_formatting(options_menu_id, options_menu.active_index, (setting,), output_pipe)
                    if options_menu.active_index == 2:
                        command = command.upper()
                        if util.is_valid_colour(command):
                            options["TEXT_COLOUR"] = command
                            send_message(output_pipe, Message.UPDATE_SETTING, ("TEXT_COLOUR", command))
                            set_menu_formatting(options_menu_id, options_menu.active_index, (command,), output_pipe)
                        else:
                            options_invalid_time = 0
                    if options_menu.active_index == 3:
                        command = command.upper()
                        if util.is_valid_colour(command):
                            options["BACKGROUND_COLOUR"] = command
                            send_message(output_pipe, Message.UPDATE_SETTING, ("BACKGROUND_COLOUR", command))
                            set_menu_formatting(options_menu_id, options_menu.active_index, (command,), output_pipe)
                        else:
                            options_invalid_time = 0
                    save_options(options)
                    command = None

        if game_state == GameState.SWITCH_LEVEL:
            if command is not None:
                if is_command_yes(command):
                    level_index += 1

                    if level_index == num_levels:
                        current_save.set_collected_gold(player_gold)
                        current_save.set_condition(Save.WON)
                        current_save.save("saves")
                        result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                        game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)
                    else:
                        game_state = GameState.SWITCH_LEVEL_FINALISE
                    current_save.set_collected_gold(player_gold)
                    current_save.set_level_index(level_index)
                    current_save.save("saves")
                else:
                    game_state = game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe)
                command = None

        if game_state == GameState.SWITCH_LEVEL_FINALISE:
            kill_level_entities(entity_list, level_entity_list, output_pipe)
            level = levels[level_index]
            spawn_level_entities(level, entity_list, level_entity_list, output_pipe)
            level_duration = 0
            player_steal_info_time = 3
            bear_spawned = False
            bear_target = None
            hide_entity(bear.get_id(), output_pipe)
            held_entity = None
            player_steal = False
            player.set_position(level.get_spawnpoint())
            player.set_rotation(0)
            game_state = game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe)

        if game_state == GameState.RESULT:
            if command is not None:
                delete_text_box(result_text_box, text_box_list, output_pipe)
                game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                command = None

        if game_state == GameState.GAME:
            if display_help:
                paused = True
                help_menu = get_by_id(help_menu_id, menu_list)
                if curr_time - input_time > input_cooldown:
                    if handle_menu_inputs(help_menu_id, menu_list, inputs, output_pipe):
                        input_time = curr_time
                if command is not None:
                    if help_menu.active_index == 0:
                        hide_menu(help_menu_id, output_pipe)
                        paused = False
                        display_help = False
                    command = None
            else:
                if command is not None:
                    command = command.upper()
                    if command == "HELP":
                        show_menu(help_menu_id, output_pipe)
                        display_help = True
                        paused = True
                    elif command == "GRAB":
                        shortest_distance = None
                        closest_entity = None
                        for entity in entity_list:
                            if entity.GRABBABLE:
                                distance = line_length(player.get_position(), entity.get_position())
                                if distance < player.REACH and (shortest_distance is None or distance < shortest_distance):
                                    shortest_distance = distance
                                    closest_entity = entity
                        held_entity = closest_entity
                    elif command == "DROP":
                        held_entity = None
                    elif command == "POUR":
                        if held_entity is not None and held_entity.__class__ == HoneyJar:
                            position = held_entity.get_position()
                            rotation = held_entity.get_rotation()
                            kill_entity(held_entity.get_id(), entity_list, output_pipe)
                            honey_spill = create_entity(HoneySpill, entity_list, output_pipe, position, rotation)
                            level_entity_list.append(honey_spill.get_id())
                    elif command == "STEAL":
                        player_steal = True
                    elif command == "QUIT":
                        game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                    command = None

        if game_state == GameState.GAME and not paused:
            level_duration += delta
            player_steal_info_time += delta

            show_information(output_pipe)
            update_information(max(0, round(30 - level_duration)), player_gold, output_pipe)

            if level_duration <= 3:
                show_text_box(bear_30s_warning, output_pipe)
            else:
                hide_text_box(bear_30s_warning, output_pipe)

            if 30 <= level_duration <= 33:
                show_text_box(bear_0s_warning, output_pipe)
            else:
                hide_text_box(bear_0s_warning, output_pipe)

            if player_steal_info_time <= 3:
                show_text_box(player_steal_info, output_pipe)
            else:
                hide_text_box(player_steal_info, output_pipe)

            if level_duration >= 30:
                if not bear_spawned:
                    bear_spawned = True
                    bear.set_position(level.get_spawnpoint())
                    show_entity(bear.get_id(), output_pipe)
            else:
                hide_entity(bear.get_id(), output_pipe)

            if inputs[LEFT]:
                player.rotate(-Player.ROTATION_SPEED)
            if inputs[RIGHT]:
                player.rotate(Player.ROTATION_SPEED)

            player_prev_position = player.get_position()

            if inputs[UP]:
                player.move_within_level(-Player.MOVEMENT_SPEED, level)
            if inputs[DOWN]:
                player.move_within_level(Player.MOVEMENT_SPEED, level)

            if player.at_exit(level):
                player.set_position(player_prev_position)
                game_state = game_state_switch_level(switch_level_warning, output_pipe)

            if held_entity is not None:
                player.hold_entity(held_entity)

            if player_steal and bear_spawned:
                if bear_target == player:
                    player_steal = False

                distance = line_length(player.get_position(), bear.get_position())

                progress = player_steal_time / PLAYER_STEAL_TIME

                if distance > player.REACH:
                    player_steal = False
                player_steal_time += delta
                update_progress_bar(player_progress_bar_id, player.get_position(), progress, output_pipe)
                show_progress_bar(player_progress_bar_id, output_pipe)

                if progress >= 1:
                    player_steal_info_time = 0
                    player_steal_time = 0
                    player_steal = False
                    player_gold += random.randint(500, 1000)
            else:
                hide_progress_bar(player_progress_bar_id, output_pipe)

            if bear_spawned:
                if bear_target is None:
                    shortest_distance = None
                    closest_entity = None
                    for entity in entity_list:
                        if entity.__class__ == HoneySpill:
                            distance = line_length(player.get_position(), entity.get_position())
                            if shortest_distance is None or distance < shortest_distance:
                                shortest_distance = distance
                                closest_entity = entity
                    bear_target = closest_entity
                    if bear_target is None:
                        bear_target = player

                if not bear.is_touching(bear_target):
                    bear.move_towards(bear_target.get_position(), level)
                    bear.get_animation().tick()
                else:
                    bear.get_animation().reset()
                    if not bear_eating and bear_target.__class__ == HoneySpill:
                        bear_eating = True
                        show_progress_bar(bear_progress_bar_id, output_pipe)
                        update_progress_bar(bear_progress_bar_id, bear.get_position(), 0, output_pipe)

                if bear_target == player and bear.is_touching(player):
                    current_save.set_condition(Save.LOST)
                    current_save.save("saves")
                    result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                    game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)
                if bear_eating:
                    bear_eating_time += delta
                    progress = bear_eating_time / BEAR_EAT_TIME
                    update_progress_bar(bear_progress_bar_id, bear.get_position(), progress, output_pipe)
                    if progress >= 1:
                        bear_eating = False
                        hide_progress_bar(bear_progress_bar_id, output_pipe)
                        kill_entity(bear_target.get_id(), entity_list, output_pipe)
                        bear_eating_time = 0
                        bear_target = None

            if inputs[UP] or inputs[DOWN]:
                player.get_animation().tick()
            else:
                player.get_animation().reset()

            for entity in entity_list:
                send_message(output_pipe, Message.ENTITY_UPDATE,
                             (entity.get_id(), entity.get_position(), entity.get_rotation()))
                send_message(output_pipe, Message.ENTITY_ANIMATE,
                             (entity.get_id(), entity.get_animation().get_current_state()))

        send_message(output_pipe, Message.DELTA, delta)