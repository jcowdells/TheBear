import json
import time
import random

import util
from game import DisplayEntity, Player, Bear, Menu, MenuInterface, TextBox, Entity, HoneyJar, HoneySpill, \
    ProgressBar, level_array, saves_array, Save
from geometry import line_length
from util import Message
from enum import Enum, auto

# Define some constants
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

# Create an entity and tell Main that it exists through the pipeline
def create_entity(entity_cls, entity_list, output_pipe, *args, visible=True):
    entity = entity_cls(*args)
    entity_list.append(entity)
    # Main only needs data such as position, rotation and the texture, so we only send it a DisplayEntity object
    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE, visible, str(entity))
    send_message(output_pipe, Message.ENTITY_CREATED, display_entity)
    return entity

# Create an entity, using a string instead of a class
def create_entity_string(entity_string, entity_list, output_pipe, *args, visible=True):
    entity = Entity.from_string(entity_string, *args)
    entity_cls = entity.__class__
    entity_list.append(entity)
    # Main only needs the DisplayEntity
    display_entity = DisplayEntity(entity.get_position(), entity.get_rotation(), entity.get_hitbox_radius(),
                                   entity_cls.SAMPLERS, entity.get_id(), entity_cls.DISPLAY_TYPE, visible, str(entity))
    send_message(output_pipe, Message.ENTITY_CREATED, display_entity)
    return entity

# Get an object by its id, from a list of objects
def get_by_id(object_id, object_list):
    for object_ in object_list:
        if object_.get_id() == object_id:
            return object_
    return None

# Tell main to display this entity
def show_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, True))

# Tell Main to hide this entity
def hide_entity(entity_id, output_pipe):
    send_message(output_pipe, Message.ENTITY_VISIBLE, (entity_id, False))

# Kill the entity, and tell Main it no longer exists
def kill_entity(entity_id, entity_list, output_pipe):
    for entity in entity_list:
        if entity.get_id() == entity_id:
            entity_list.remove(entity)
            break
    send_message(output_pipe, Message.ENTITY_KILL, entity_id)

# Create a menu, and tell main it exists
def create_menu(menu_list, output_pipe, *args, **kwargs):
    menu = Menu(*args, **kwargs)
    menu_size = menu.get_num_items()
    menu_index = menu.get_active_index()
    menu_id = menu.get_id()
    # Physics only cares about the active index and number of indices, so only a MenuInterface is kept
    menu_interface = MenuInterface(menu_size, menu_index, menu_id)
    menu_list.append(menu_interface)
    send_message(output_pipe, Message.MENU_CREATED, menu)
    return menu_id

# Create a menu from a json file
def create_menu_from_file(menu_list, output_pipe, *args, **kwargs):
    menu = Menu.from_file(*args, **kwargs)
    menu_size = menu.get_num_items()
    menu_index = menu.get_active_index()
    menu_id = menu.get_id()
    # Physics only needs a MenuInterface
    menu_interface = MenuInterface(menu_size, menu_index, menu_id)
    menu_list.append(menu_interface)
    send_message(output_pipe, Message.MENU_CREATED, menu)
    return menu_id

# Add an item to a menu
def add_item_to_menu(menu_id, menu_list, menu_item, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    menu_interface.set_num_items(menu_interface.get_num_items() + 1)
    # Tell the menu interface that there are more items, but we don't care what the item is
    send_message(output_pipe, Message.MENU_ADD_ITEM, (menu_id, menu_item))

# Remove an item from a menu
def remove_item_from_menu(menu_id, menu_list, menu_index, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    menu_interface.set_num_items(menu_interface.get_num_items() - 1)
    # Tell the menu interface there are fewer items
    if menu_interface.get_active_index() >= menu_interface.get_num_items():
        menu_interface.set_active_index(menu_interface.get_active_index() - 1)
        send_message(output_pipe, Message.MENU_CHANGE_INDEX, (menu_id, menu_interface.get_active_index()))
        # If index is now outside the list, bring it back
    send_message(output_pipe, Message.MENU_REMOVE_ITEM, (menu_id, menu_index))

# Set the active index of a menu
def set_active_index_menu(menu_id, menu_list, menu_index, output_pipe):
    menu_interface = get_by_id(menu_id, menu_list)
    if menu_interface is None:
        return
    if menu_index < menu_interface.get_num_items():
        menu_interface.set_active_index(menu_index)
        send_message(output_pipe, Message.MENU_CHANGE_INDEX, (menu_id, menu_index))

# Handle the menu inputs, and adjust the active index accordingly
def handle_menu_inputs(menu_id, menu_list, inputs, output_pipe):
    menu = get_by_id(menu_id, menu_list)
    if inputs[UP]:
        if menu.get_active_index() > 0:
            set_active_index_menu(menu_id, menu_list, menu.get_active_index() - 1, output_pipe)
        return True
    if inputs[DOWN]:
        if menu.get_active_index() < menu.get_num_items() - 1:
            set_active_index_menu(menu_id, menu_list, menu.get_active_index() + 1, output_pipe)
        return True
    return False

# Tell Main to display a menu
def show_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, True))

# Tell Main to stop showing a menu
def hide_menu(menu_id, output_pipe):
    send_message(output_pipe, Message.MENU_VISIBLE, (menu_id, False))

# Format a menu, if a description contains '{}' then it will be changed to the formatted string
def set_menu_formatting(menu_id, format_index, formatting, output_pipe):
    send_message(output_pipe, Message.MENU_SET_FORMATTING, (menu_id, format_index, formatting))

# Create a text box and tell Main it exists
def create_text_box(text_box_list, output_pipe, *args, **kwargs):
    text_box = TextBox(*args, **kwargs)
    text_box_id = text_box.get_id()
    send_message(output_pipe, Message.TEXT_BOX_CREATED, text_box)
    # We only need to store the id, to allow for communications with Main
    text_box_list.append(text_box_id)
    return text_box_id

# Tell main to display a text box
def show_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, True))

# Tell main to hide a text box
def hide_text_box(text_box_id, output_pipe):
    send_message(output_pipe, Message.TEXT_BOX_VISIBLE, (text_box_id, False))

# Tell main to hide all text boxes in a list
def hide_all_text_boxes(text_box_list, output_pipe):
    for text_box in text_box_list:
        hide_text_box(text_box, output_pipe)

# Tell main that a text box no longer exists
def delete_text_box(text_box_id, text_box_list, output_pipe):
    text_box_list.remove(text_box_id)
    send_message(output_pipe, Message.TEXT_BOX_DELETED, text_box_id)

# Tell main to display all entities in a list
def show_all_entities(entity_list, output_pipe):
    for entity in entity_list:
        show_entity(entity.get_id(), output_pipe)

# Tell main to hide all entities in a list
def hide_all_entities(entity_list, output_pipe):
    for entity in entity_list:
        hide_entity(entity.get_id(), output_pipe)

# Tell main to create a progress bar
def create_progress_bar(progress_bar_list, output_pipe, *args, **kwargs):
    progress_bar = ProgressBar(*args, **kwargs)
    progress_bar_id = progress_bar.get_id()
    send_message(output_pipe, Message.PROGRESS_BAR_CREATED, progress_bar)
    progress_bar_list.append(progress_bar_id)
    return progress_bar_id

# Tell main to update a progress bar's position and progress
def update_progress_bar(progress_bar_id, position, progress, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_UPDATE, (progress_bar_id, position, progress))

# Tell main to display a progress bar
def show_progress_bar(progress_bar_id, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_VISIBLE, (progress_bar_id, True))

# Tell main to hide a progress bar
def hide_progress_bar(progress_bar_id, output_pipe):
    send_message(output_pipe, Message.PROGRESS_BAR_VISIBLE, (progress_bar_id, False))

# Tell main to hide all progress bars in a list
def hide_all_progress_bars(progress_bar_list, output_pipe):
    for progress_bar in progress_bar_list:
        hide_progress_bar(progress_bar, output_pipe)

# Tell main to show level information such as gold collected and time remaining
def show_information(output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", True))

# Tell main to hide the information
def hide_information(output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", False))

# Tell main to update the information it is displaying
def update_information(time_remaining, collected_gold, output_pipe):
    send_message(output_pipe, Message.UPDATE_SETTING, ("TIME_REMAINING", time_remaining))
    send_message(output_pipe, Message.UPDATE_SETTING, ("COLLECTED_GOLD", collected_gold))

# Tell main to kill all entities in a list
def kill_level_entities(entity_list, level_entity_list, output_pipe):
    for entity_id in level_entity_list:
        kill_entity(entity_id, entity_list, output_pipe)

# Tell main to spawn all the entities contained in a level
def spawn_level_entities(level, entity_list, level_entity_list, output_pipe):
    for entity_type, position in level.iter_entities():
        entity = create_entity_string(entity_type, entity_list, output_pipe, position, 0, visible=True)
        level_entity_list.append(entity.get_id())

# Create a new save file
def create_save(saves, save_name):
    save = Save(save_name, 0, 0)
    saves.append(save)
    return save

# Add a save file to the game menu
def add_save_to_menu(save, menu_id, menu_list, output_pipe):
    add_item_to_menu(menu_id, menu_list, (save.get_save_name(), None), output_pipe)

# Receive a message from main
def recv_message(input_pipe):
    return input_pipe.recv()

# Send a message to main
def send_message(output_pipe, message, value):
    output_pipe.send((message, value))

# Hide all text boxes, progress bars and menus
def hide_all(text_box_list, progress_bar_list, menu_list, output_pipe):
    hide_all_text_boxes(text_box_list, output_pipe)
    hide_all_progress_bars(progress_bar_list, output_pipe)
    for menu in menu_list:
        hide_menu(menu.get_id(), output_pipe)

# Create a text box displaying the results of a game
def create_result_text_box(text_box_list, current_save, output_pipe):
    if current_save.get_condition() == Save.WON:
        return create_text_box(text_box_list, output_pipe,
                        "CONGRATULATIONS",
                        f"You survived, and stole {current_save.get_collected_gold()} gold from the bear! Press ENTER to return to the main menu")
    elif current_save.get_condition() == Save.LOST:
        return create_text_box(text_box_list, output_pipe,
                        "DISAPPOINTING...",
                        f"You lost the game. California state recovered what remained of your body. Press ENTER to return to the main menu")

# Switch to main menu
def game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe):
    hide_all(text_box_list, progress_bar_list, menu_list, output_pipe)
    send_message(output_pipe, Message.UPDATE_SETTING, ("DISPLAY_INFO", False))
    if current_save is not None:
        current_save.save("saves")
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.MAIN_MENU)
    return GameState.MAIN_MENU

# Switch to the results page
def game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe):
    hide_all(text_box_list, progress_bar_list, menu_list, output_pipe)
    show_text_box(result_text_box, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.RESULT)
    return GameState.RESULT

# Switch to the game selection menu
def game_state_game_select(games_menu_id, output_pipe):
    show_menu(games_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.GAME_SELECT)
    return GameState.GAME_SELECT

# Switch to the options menu
def game_state_options_select(options_menu_id, output_pipe):
    show_menu(options_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.OPTIONS_SELECT)
    return GameState.OPTIONS_SELECT

# Switch to the tutorial question box
def game_state_tutorial_select(games_menu_id, tutorial_question_id, save_warning_id, output_pipe):
    hide_menu(games_menu_id, output_pipe)
    hide_text_box(save_warning_id, output_pipe)
    show_text_box(tutorial_question_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.TUTORIAL_SELECT)
    return GameState.TUTORIAL_SELECT

# Switch to the tutorial menu
def game_state_tutorial_view(tutorial_question_id, tutorial_menu_id, output_pipe):
    hide_text_box(tutorial_question_id, output_pipe)
    show_menu(tutorial_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.TUTORIAL_VIEW)
    return GameState.TUTORIAL_VIEW

# Switch to the main game
def game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe):
    hide_text_box(switch_level_warning, output_pipe)
    hide_text_box(tutorial_question_id, output_pipe)
    hide_menu(games_menu_id, output_pipe)
    hide_menu(tutorial_menu_id, output_pipe)
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.GAME)
    show_all_entities(entity_list, output_pipe)
    return GameState.GAME

# Switch to a different level
def game_state_switch_level(switch_level_warning, output_pipe):
    send_message(output_pipe, Message.GAME_STATE_CHANGED, GameState.SWITCH_LEVEL)
    show_text_box(switch_level_warning, output_pipe)
    return GameState.SWITCH_LEVEL

# Check if a command entered is yes, YES, Y, y etc
def is_command_yes(command):
    return len(command) > 0 and command[0].upper() == "Y"

# Load the options stored in the options file
def load_options():
    filepath = util.abspath("res/options.json")
    with open(filepath, "r") as file:
        options = json.load(file)
    return options

# Save the current options to the options file
def save_options(options):
    filepath = util.abspath("res/options.json")
    with open(filepath, "w", encoding="utf-8") as file:
        json.dump(options, file, ensure_ascii=False)

# The main physics thread
# This will run in parallel to the window, so fps can be independent of game calculations etc
def physics_thread(input_pipe, output_pipe):
    # Do some time stuff
    timestep = TIMESTEP
    prev_time = time.perf_counter()

    # Create lists for different objects
    entity_list = []
    level_entity_list = []
    menu_list = []
    text_box_list = []
    progress_bar_list = []

    # Store user inputs
    input_cooldown = 0.2
    input_time = time.perf_counter()
    inputs = {
        UP:    False,
        DOWN:  False,
        LEFT:  False,
        RIGHT: False
    }
    command = None

    # Load options
    options = load_options()
    options_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/options.json", visible=False)
    options_invalid_id = create_text_box(text_box_list, output_pipe, "ERROR", "Invalid input.", visible=False)
    options_invalid_time = 3
    count = 1
    for key, value in options.items():
        send_message(output_pipe, Message.UPDATE_SETTING, (key, value))
        set_menu_formatting(options_menu_id, count, (value,), output_pipe)
        count += 1

    # Store the levels
    levels = level_array("res/levels")
    num_levels = len(levels)
    level_index = 0
    level = levels[level_index]
    level_duration = 0
    spawn_level_entities(level, entity_list, level_entity_list, output_pipe)

    # Set the game state
    game_state = GameState.MAIN_MENU
    send_message(output_pipe, Message.GAME_STATE_CHANGED, game_state)
    send_message(output_pipe, Message.LEVEL_CHANGED, level)

    # Store some information about the player
    player = create_entity(Player, entity_list, output_pipe, (0, 0), 0, visible=False)
    send_message(output_pipe, Message.FOCUS_ID, player.get_id())
    player_progress_bar_id = create_progress_bar(progress_bar_list, output_pipe, player.get_position(), 0.1, visible=False)
    held_entity = None
    player_steal = False
    player_steal_time = 0
    player_steal_info_time = 3
    player_gold = 0

    # Store some information about the bear
    bear = create_entity(Bear, entity_list, output_pipe, (-5, -5), 0, visible=False)
    bear_progress_bar_id = create_progress_bar(progress_bar_list, output_pipe, bear.get_position(), 0.1, visible=False)
    bear_target = None
    bear_eating_time = 0
    bear_eating = False
    bear_spawned = False

    # Sort out the menus and text boxes
    main_menu_selector = 0
    tutorial_question_id = create_text_box(text_box_list, output_pipe,
                                           "READ TUTORIAL", "Would you like to read the tutorial?\n\nEnter yes/no into the console",
                                           visible=False)
    tutorial_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/tutorial.json", visible=False)
    help_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/help.json", visible=False)
    bear_30s_warning = create_text_box(text_box_list, output_pipe,"INFORMATION", "The Bear is arriving in 30 seconds!", visible=False)
    bear_0s_warning = create_text_box(text_box_list, output_pipe,"INFORMATION", "The Bear has arrived!", visible=False)
    player_steal_info = create_text_box(text_box_list, output_pipe,"INFORMATION", "You stole some gold!", visible=False)
    games_menu_id = create_menu_from_file(menu_list, output_pipe, "res/menus/select_game.json", visible=False)
    switch_level_warning = create_text_box(text_box_list, output_pipe,
                                           "WARNING",
                                           "Are you sure you want to progress to the next level? Enter yes/no into the console",
                                           visible=False)
    save_warning_time = 3
    save_warning_id = create_text_box(text_box_list, output_pipe, "ERROR", "Cannot create a save file without a name!",
                                      visible=False)
    result_text_box = -1

    # Create saves
    saves_list = saves_array("saves")
    current_save = None
    for save in saves_list:
        add_save_to_menu(save, games_menu_id, menu_list, output_pipe)

    # Set some boolean flags
    running = True
    paused  = False
    display_help = False

    # Loop while physics is active
    while running:
        # Get messages from main
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

        # Find the change in time between previous loop
        curr_time = time.perf_counter()
        delta = curr_time - prev_time
        if delta < timestep:
            # If the time is less than the physics fixed timestep, then we don't need to run physics
            continue
        prev_time = curr_time

        # Main menu game state
        if game_state == GameState.MAIN_MENU:
            if curr_time - input_time > input_cooldown:
                # Update menu position based on inputs
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
                    if main_menu_selector == 0: # Play button
                        game_state = game_state_game_select(games_menu_id, output_pipe)
                    elif main_menu_selector == 1: # Options button
                        game_state = game_state_options_select(options_menu_id, output_pipe)
                    elif main_menu_selector == 2: # Quit button
                        send_message(output_pipe, Message.EXIT, 0)
                    command = None

        # Game selector game state
        if game_state == GameState.GAME_SELECT:
            save_warning_time += delta
            if save_warning_time < 3:
                # Display error for 3 seconds if there is an error in the save name
                show_text_box(save_warning_id, output_pipe)
            else:
                hide_text_box(save_warning_id, output_pipe)
            games_menu = get_by_id(games_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(games_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if games_menu.get_active_index() == 0: # Go back
                        hide_menu(games_menu_id, output_pipe)
                        game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                    elif games_menu.get_active_index() == 1: # New game
                        if command != "":
                            current_save = create_save(saves_list, command)
                            add_save_to_menu(current_save, games_menu_id, menu_list, output_pipe)

                            current_save.save("saves")
                            save_warning_time = 3
                            game_state = game_state_tutorial_select(games_menu_id, tutorial_question_id, save_warning_id, output_pipe)
                        else:
                            save_warning_time = 0
                    else: # Load from save
                        if command.upper() == "DELETE":
                            delete_index = games_menu.get_active_index() - 2
                            delete_save = saves_list[delete_index]
                            delete_save.delete("saves")
                            current_save = None
                            saves_list.pop(delete_index)
                            remove_item_from_menu(games_menu_id, menu_list, games_menu.get_active_index(), output_pipe)
                        else:
                            current_save = saves_list[games_menu.get_active_index() - 2]
                            if current_save.get_condition() != Save.PLAYING:
                                result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                                game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)
                            else:
                                game_state = GameState.SWITCH_LEVEL_FINALISE
                    command = None

        # Tutorial yes/no game state
        if game_state == GameState.TUTORIAL_SELECT:
            if command is not None:
                if is_command_yes(command):
                    game_state = game_state_tutorial_view(tutorial_question_id, tutorial_menu_id, output_pipe)
                else:
                    game_state = GameState.SWITCH_LEVEL_FINALISE
                command = None

        # View tutorial game state
        if game_state == GameState.TUTORIAL_VIEW:
            tutorial_menu = get_by_id(tutorial_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(tutorial_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if tutorial_menu.get_active_index() == 0:
                        game_state = GameState.SWITCH_LEVEL_FINALISE

        # Change options game state
        if game_state == GameState.OPTIONS_SELECT:
            options_invalid_time += delta
            if options_invalid_time < 3: # Display warning for 3 seconds if option is invalid
                show_text_box(options_invalid_id, output_pipe)
            else:
                hide_text_box(options_invalid_id, output_pipe)
            options_menu = get_by_id(options_menu_id, menu_list)
            if curr_time - input_time > input_cooldown:
                if handle_menu_inputs(options_menu_id, menu_list, inputs, output_pipe):
                    input_time = curr_time
                if command is not None:
                    if options_menu.get_active_index() == 0: # Go back
                        hide_menu(options_menu_id, output_pipe)
                        game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                        options_invalid_time = 3
                    if options_menu.get_active_index() == 1: # Display FPS
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
                            set_menu_formatting(options_menu_id, options_menu.get_active_index(), (setting,), output_pipe)
                    if options_menu.get_active_index() == 2: # Text colour
                        command = command.upper()
                        if util.is_valid_colour(command):
                            options["TEXT_COLOUR"] = command
                            send_message(output_pipe, Message.UPDATE_SETTING, ("TEXT_COLOUR", command))
                            set_menu_formatting(options_menu_id, options_menu.get_active_index(), (command,), output_pipe)
                        else:
                            options_invalid_time = 0
                    if options_menu.get_active_index() == 3: # Background colour
                        command = command.upper()
                        if util.is_valid_colour(command):
                            options["BACKGROUND_COLOUR"] = command
                            send_message(output_pipe, Message.UPDATE_SETTING, ("BACKGROUND_COLOUR", command))
                            set_menu_formatting(options_menu_id, options_menu.get_active_index(), (command,), output_pipe)
                        else:
                            options_invalid_time = 0
                    if options_menu.get_active_index() == 4: # Font size
                        try:
                            font_size = int(command)
                        except ValueError:
                            font_size = None
                        if font_size is not None:
                            options["FONT_SIZE"] = font_size
                            send_message(output_pipe, Message.UPDATE_SETTING, ("FONT_SIZE", font_size))
                            set_menu_formatting(options_menu_id, options_menu.get_active_index(), (font_size,), output_pipe)
                        else:
                            options_invalid_time = 0
                    save_options(options)
                    command = None

        # Switch level game state
        if game_state == GameState.SWITCH_LEVEL:
            if command is not None:
                if is_command_yes(command):
                    level_index += 1

                    if level_index >= num_levels:
                        level_index = num_levels - 1
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

        # Finish switching levels, can be reached from either main menu or when level advances
        if game_state == GameState.SWITCH_LEVEL_FINALISE:
            if level_index >= num_levels:
                result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)

            player_gold = current_save.get_collected_gold()
            level_index = current_save.get_level_index()

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
            send_message(output_pipe, Message.LEVEL_CHANGED, level)
            game_state = game_state_game(tutorial_question_id, tutorial_menu_id, switch_level_warning, games_menu_id, entity_list, output_pipe)

        # Display result game state
        if game_state == GameState.RESULT:
            if command is not None:
                delete_text_box(result_text_box, text_box_list, output_pipe)
                game_state = game_state_main_menu(text_box_list, progress_bar_list, menu_list, current_save, output_pipe)
                command = None

        # In game game state
        if game_state == GameState.GAME:
            if display_help: # If help menu is open
                paused = True
                help_menu = get_by_id(help_menu_id, menu_list)
                if curr_time - input_time > input_cooldown:
                    if handle_menu_inputs(help_menu_id, menu_list, inputs, output_pipe):
                        input_time = curr_time
                if command is not None:
                    if help_menu.get_active_index() == 0: # Exit the help menu
                        hide_menu(help_menu_id, output_pipe)
                        paused = False
                        display_help = False
                    command = None
            else:
                if command is not None:
                    command = command.upper()
                    # Process any commands the user has entered
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
                    elif command == "EASTEREGG":
                        send_message(output_pipe, Message.UPDATE_SETTING, ("EASTER_EGG", True))
                    command = None

        # In game game state, when game is not paused
        if game_state == GameState.GAME and not paused:
            # Increment timers
            level_duration += delta
            player_steal_info_time += delta

            update_information(max(0, round(30 - level_duration)), player_gold, output_pipe)
            show_information(output_pipe) # Show game statistics

            # Display 30s warning for first 2 seconds
            if level_duration <= 2:
                show_text_box(bear_30s_warning, output_pipe)
            else:
                hide_text_box(bear_30s_warning, output_pipe)

            # Display bear arrived for two seconds after bear arrives
            if 30 <= level_duration <= 32:
                show_text_box(bear_0s_warning, output_pipe)
            else:
                hide_text_box(bear_0s_warning, output_pipe)

            # Show gold has been stolen for a second after it's stolen
            if player_steal_info_time <= 1:
                show_text_box(player_steal_info, output_pipe)
            else:
                hide_text_box(player_steal_info, output_pipe)

            # Spawn bear after 30 seconds
            if level_duration >= 30:
                if not bear_spawned:
                    pass
                    #bear_spawned = True
                    #bear.set_position(level.get_spawnpoint())
                    #show_entity(bear.get_id(), output_pipe)
            else:
                hide_entity(bear.get_id(), output_pipe)

            # Rotate player if user input says so
            if inputs[LEFT]:
                player.rotate(-Player.ROTATION_SPEED)
            if inputs[RIGHT]:
                player.rotate(Player.ROTATION_SPEED)

            # Keep previous position before movement
            player_prev_position = player.get_position()

            # Move forwards or backwards depending on inputs
            if inputs[UP]:
                player.move_within_level(-Player.MOVEMENT_SPEED, level)
            if inputs[DOWN]:
                player.move_within_level(Player.MOVEMENT_SPEED, level)

            # Ask for confirmation to leave if exiting level
            if player.at_exit(level):
                player.set_position(player_prev_position) # Move out of collision with wall, otherwise will get stuck in this menu forever
                hide_all_progress_bars(progress_bar_list, output_pipe)
                game_state = game_state_switch_level(switch_level_warning, output_pipe)

            # Move held entity to above player's head
            if held_entity is not None:
                player.hold_entity(held_entity)

            if bear_target == player: # Don't allow theft while the bear is targeting you
                player_steal = False

            # If player is stealing gold
            if player_steal and bear_spawned:
                distance = line_length(player.get_position(), bear.get_position())
                progress = player_steal_time / PLAYER_STEAL_TIME

                if distance > player.REACH: # Stop the player stealing if the bear is too far away
                    player_steal = False
                player_steal_time += delta # Increment stealing time
                update_progress_bar(player_progress_bar_id, player.get_position(), progress, output_pipe)
                show_progress_bar(player_progress_bar_id, output_pipe)

                if progress >= 1: # If stealing is complete
                    player_steal_info_time = 0
                    player_steal_time = 0
                    player_steal = False
                    player_gold += random.randint(500, 1000) # Give the player some gold
            else:
                hide_progress_bar(player_progress_bar_id, output_pipe)

            if bear_spawned:
                if bear_target is None: # If bear has no current target
                    shortest_distance = None
                    closest_entity = None
                    for entity in entity_list:
                        if entity.__class__ == HoneySpill: # Find a honey spill to target
                            distance = line_length(player.get_position(), entity.get_position())
                            if shortest_distance is None or distance < shortest_distance:
                                shortest_distance = distance
                                closest_entity = entity
                    bear_target = closest_entity
                    if bear_target is None: # If no honey spills are left, target the player
                        bear_target = player

                if not bear.is_touching(bear_target): # Move towards target until touching it
                    bear.move_towards_target(bear_target.get_position(), level)
                    bear.get_animation().tick()
                else: # If bear is touching its target
                    bear.get_animation().reset()
                    if not bear_eating and bear_target.__class__ == HoneySpill: # Make bear eat honey if it touches it
                        bear_eating = True
                        show_progress_bar(bear_progress_bar_id, output_pipe)
                        update_progress_bar(bear_progress_bar_id, bear.get_position(), 0, output_pipe)

                # If bear reaches player while targeting them, end the game
                if bear_target == player and bear.is_touching(player):
                    current_save.set_condition(Save.LOST)
                    current_save.save("saves")
                    result_text_box = create_result_text_box(text_box_list, current_save, output_pipe)
                    game_state = game_state_result(text_box_list, progress_bar_list, menu_list, result_text_box, output_pipe)

                if bear_eating:
                    bear_eating_time += delta # Increment timer
                    progress = bear_eating_time / BEAR_EAT_TIME
                    update_progress_bar(bear_progress_bar_id, bear.get_position(), progress, output_pipe)
                    if progress >= 1: # If finished eating
                        bear_eating = False
                        hide_progress_bar(bear_progress_bar_id, output_pipe)
                        kill_entity(bear_target.get_id(), entity_list, output_pipe)
                        bear_eating_time = 0
                        bear_target = None

            # Run animation if inputs pressed
            if inputs[UP] or inputs[DOWN]:
                player.get_animation().tick()
            else:
                player.get_animation().reset()

            # Update entities in main
            for entity in entity_list:
                send_message(output_pipe, Message.ENTITY_UPDATE,
                             (entity.get_id(), entity.get_position(), entity.get_rotation()))
                send_message(output_pipe, Message.ENTITY_ANIMATE,
                             (entity.get_id(), entity.get_animation().get_current_state()))

        send_message(output_pipe, Message.DELTA, delta)
