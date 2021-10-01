import pygame   # Using pygame module to draw everything on the screen for the player to see
import random   # Using random module for randomizing the mines' locations
import pickle   # Using pickle to save and load data from encrypted files
import pathlib  # Using pathlib to check if a file exists


class AnimatedImage:
    def __init__(self, x: int, y: int, frames: list):
        self.x, self.y = x, y
        self.frames    = frames
        self.frame     = 0

    def show(self, surface: pygame.Surface, width: int, height: int, elapsed_time: float):
        surface.blit(self.frames[int(self.frame)], (self.x * width, self.y * height))

        if self.frame < len(self.frames)-1:
            self.frame += elapsed_time/15
        else:
            self.frame = len(self.frames)-1

    def update_frames(self, updated_frames: list):
        self.frames = updated_frames


def generate_mines(amount_of_mines: int, x_grid_size: int, y_grid_size: int, avoid_locations: list):
    available_locations = [(x, y) for x in range(x_grid_size) for y in range(y_grid_size)]
    hint_numbers        = [[0 for _ in range(x_grid_size)] for _ in range(y_grid_size)]
    mines_locations     = []

    for location_to_avoid in avoid_locations:
        if 0 < location_to_avoid[0]+1 < x_grid_size+1 and 0 < location_to_avoid[1]+1 < y_grid_size+1:
            available_locations.remove(location_to_avoid)

    for mine in range(amount_of_mines):
        mine_location = random.choice(available_locations)
        available_locations.pop(available_locations.index(mine_location))
        mines_locations.append(mine_location)

        # If the number is negative, there is a bomb in the tile, so in order to keep the number negative,
        # it must be below -8 because 0 is an empty tile. THIS WORKS! It COULD be something much more convenient
        # but it works and that's all that matters
        hint_numbers[mine_location[1]][mine_location[0]] = -9

        # Top left
        if mine_location[1] > 0:
            if mine_location[0] > 0:
                hint_numbers[mine_location[1]-1][mine_location[0]-1] \
                    = hint_numbers[mine_location[1]-1][mine_location[0]-1]+1

            # Top
            hint_numbers[mine_location[1] - 1][mine_location[0]] \
                = hint_numbers[mine_location[1] - 1][mine_location[0]] + 1

            # Top right
            if mine_location[0] < x_grid_size-1:
                hint_numbers[mine_location[1]-1][mine_location[0]+1] \
                    = hint_numbers[mine_location[1]-1][mine_location[0]+1]+1

        # Right
        if mine_location[0] < x_grid_size-1:
            hint_numbers[mine_location[1]][mine_location[0]+1] \
                = hint_numbers[mine_location[1]][mine_location[0]+1]+1

        # Bottom right
        if mine_location[1] < y_grid_size-1:
            if mine_location[0] < x_grid_size-1:
                hint_numbers[mine_location[1]+1][mine_location[0]+1] \
                    = hint_numbers[mine_location[1]+1][mine_location[0]+1]+1

            # Bottom
            hint_numbers[mine_location[1] + 1][mine_location[0]] \
                = hint_numbers[mine_location[1] + 1][mine_location[0]] + 1

            # Bottom left
            if mine_location[0] > 0:
                hint_numbers[mine_location[1]+1][mine_location[0]-1] \
                    = hint_numbers[mine_location[1]+1][mine_location[0]-1]+1

        # Left
        if mine_location[0] > 0:
            if mine_location[0] > 0:
                hint_numbers[mine_location[1]][mine_location[0]-1] \
                    = hint_numbers[mine_location[1]][mine_location[0]-1]+1

    return mines_locations, hint_numbers


def draw_grid(root: pygame.Surface, x_grids: int, y_grids: int):
    display_size = root.get_size()

    line_thickness = int(display_size[0] / (x_grids*10))
    if line_thickness < 1:
        line_thickness = 1
    elif line_thickness > 3:
        line_thickness = 3

    for x in range(x_grids+1):
        pygame.draw.line(
            root, (0, 160, 0),
            (x*(display_size[0]/x_grids), 0),
            (x*(display_size[0]/x_grids), display_size[1]),
            line_thickness
        )

    for y in range(y_grids+1):
        pygame.draw.line(
            root, (0, 160, 0),
            (0, y*(display_size[1]/y_grids)),
            (display_size[0], y*(display_size[1]/y_grids)),
            line_thickness
        )


def main():
    pygame.init()
    pygame.display.set_caption("Minesweeper")

    display = pygame.display.set_mode((800, 650), pygame.RESIZABLE)

    pygame.display.set_icon(
        pygame.image.load("lib/images/minesweeper_logo.png")
    )

    gameboard             = pygame.Surface((560, 560))
    clock, elapsed_time   = pygame.time.Clock(), 0
    time, time_record     = 0, None

    # Check if a savefile can be found and if so, load the saved time record as the time record
    try:
        if pathlib.Path("minesweeper.save").exists():
            with open("minesweeper.save", "rb") as savefile:
                time_record = pickle.load(savefile)
                savefile.close()
    except Exception:
        # There has been an error loading the file, if the code in this block is executed.
        # Possibly due to the user trying to modify the save file, as it cannot be modified or it will be corrupted
        pass

    process_interrupted   = False
    game_started          = False
    game_over             = False

    # -----------------------------------------------------

    display_size             = display.get_size()
    display_previous_size    = display_size

    gameboard_size           = gameboard.get_size()
    x_grid_size, y_grid_size = 15, 15
    x_box_size               = gameboard_size[0] / x_grid_size
    y_box_size               = gameboard_size[1] / y_grid_size

    hover                    = pygame.Surface((x_box_size, y_box_size), pygame.SRCALPHA)

    hover.fill((0, 0, 0, 40))

    const_amount_of_mines             = 30  # This value should not be modified

    amount_of_mines = amount_of_flags = const_amount_of_mines
    mines_locations, hint_numbers     = None, None

    flagged_tiles                     = []
    flipped_tiles                     = []
    incorrect_tiles                   = []

    # -----------------------------------------------------

    initializing_game    = True
    animated_images      = {}

    flag_sprite          = []
    flag_sprite_img      = pygame.image.load("lib/images/flag_sprite.png").convert_alpha()

    mine_image_original  = pygame.image.load("lib/images/mine.png").convert_alpha()
    mine_image           = mine_image_original

    trophy_icon_original = pygame.image.load("lib/images/trophy.png").convert_alpha()
    trophy_icon          = trophy_icon_original

    clock_icon_original  = pygame.image.load("lib/images/clock.png").convert_alpha()
    clock_icon           = clock_icon_original

    flag_icon_original   = pygame.image.load("lib/images/flag.png").convert_alpha()
    flag_icon            = flag_icon_original

    hint_number_font    = pygame.font.Font("lib/fonts/hint_number_font.ttf", int(x_box_size / 1.5))
    score_font          = pygame.font.Font("lib/fonts/score_font.ttf", int(x_box_size / 1.3))
    incorrect_flag_font = pygame.font.Font("lib/fonts/x.ttf", int(x_box_size))

    # -----------------------------------------------------

    # TODO: Game over screen that possibly slides from right/left and goes to left/right with a button to
    #  restart the game and some text with it? Or the game over screen could also fade in and out?

    while not process_interrupted:
        # Variables that need updating in case the display size changes

        if initializing_game or display.get_size() != display_previous_size:
            initializing_game = False if initializing_game is True else False

            # Rescale / Initialize surfaces ---------------

            display_size = display_previous_size = display.get_size()

            if display.get_size()[0] >= display.get_size()[1]:
                gameboard_size = (int(display_size[1] * 0.7), int(display_size[1] * 0.7))
            else:
                gameboard_size = (int(display_size[0] * 0.7), int(display_size[0] * 0.7))

            gameboard  = pygame.transform.scale(gameboard, gameboard_size)

            x_box_size = gameboard_size[0] / x_grid_size
            y_box_size = gameboard_size[1] / y_grid_size

            hover      = pygame.transform.scale(hover, (round(x_box_size), round(y_box_size)))

            # Rescale / Initialize images -----------------

            # Recreate new images instead of scaling them because scaling multiple times makes
            # the picture quality very bad
            flag_sprite.clear()
            for frame in range(10):
                flag = pygame.Surface((flag_sprite_img.get_width(), flag_sprite_img.get_width()), pygame.SRCALPHA)
                flag.blit(
                    flag_sprite_img, (0, 0), (
                        0, frame * (flag_sprite_img.get_height() / 10),
                        flag_sprite_img.get_width(), flag_sprite_img.get_height() / 10
                    )
                )

                flag_sprite.append(
                    pygame.transform.scale(flag, (int(x_box_size), int(y_box_size)))
                )

            for animated_image in list(animated_images.keys()):
                if animated_image in flagged_tiles:
                    animated_images[animated_image].update_frames(flag_sprite)

            mine_image = pygame.transform.scale(
                mine_image_original, (int(x_box_size), int(y_box_size))
            )

            trophy_icon = pygame.transform.scale(
                trophy_icon_original, (int(x_box_size), (int(y_box_size)))
            )

            clock_icon = pygame.transform.scale(
                clock_icon_original, (int(x_box_size), int(y_box_size))
            )

            flag_icon  = pygame.transform.scale(
                flag_icon_original, (int(x_box_size), int(y_box_size))
            )

            # Rescale / Initialize fonts ------------------

            hint_number_font    = pygame.font.Font("lib/fonts/hint_number_font.ttf", int(x_box_size / 1.5))
            score_font          = pygame.font.Font("lib/fonts/score_font.ttf", int(x_box_size / 1.3))
            incorrect_flag_font = pygame.font.Font("lib/fonts/x.ttf", int(x_box_size))

        # -------------------------------------------------

        pygame.display.set_caption(f"Minesweeper    FPS {int(clock.get_fps())}")
        mouse_position              = pygame.mouse.get_pos()
        mouse_position_on_gameboard = (
            mouse_position[0] - (display_size[0]-gameboard_size[0])/2,
            mouse_position[1] - (display_size[1]-gameboard_size[1])/2
        )

        # Scoreboard --------------------------------------

        scoreboard_location = (x_box_size, y_box_size)
        scoreboard_items    = [
            (trophy_icon, score_font.render(str(time_record).lower(), True, (0, 0, 0))),
            (clock_icon, score_font.render(f"{time:.1f}",             True, (0, 0, 0))),
            (flag_icon, score_font.render(str(amount_of_flags),       True, (0, 0, 0)))
        ]

        if not game_over and game_started:
            time += elapsed_time/1000   # Elapsed time is in milliseconds, divide by 1000 to convert it to seconds

        # Display -----------------------------------------

        display.fill((0, 160, 0))

        for scoreboard_item in range(len(scoreboard_items)):
            display.blit(
                scoreboard_items[scoreboard_item][0], (
                    scoreboard_location[0],
                    scoreboard_location[1] + (scoreboard_items[scoreboard_item][0].get_height() * scoreboard_item))
            )

            text      = scoreboard_items[scoreboard_item][1]
            text_rect = text.get_rect(
                x=(scoreboard_location[0] + (scoreboard_items[scoreboard_item][0].get_width()*1.3)),
                centery=(
                    scoreboard_location[1] + (scoreboard_items[scoreboard_item][0].get_height() * scoreboard_item)
                    + scoreboard_items[scoreboard_item][0].get_height() / 2
                )
            )

            display.blit(text, text_rect)

        # Gameboard ---------------------------------------

        gameboard.fill((0, 200, 0))

        for flipped_tile in flipped_tiles:
            pygame.draw.rect(
                gameboard, (230, 200, 160), (
                    round(flipped_tile[0]*x_box_size), round(flipped_tile[1]*y_box_size),
                    round(x_box_size),                 round(y_box_size)
                )
            )

        for animated_image in animated_images:
            animated_images[animated_image].show(gameboard, x_box_size, y_box_size, elapsed_time)

            # Check if an image is in the same position as a tile that is flagged.
            # If so, the current image should be a flag.
            if game_over and animated_image in flagged_tiles:
                # If the game has ended, check if there are any flags in incorrect locations
                if animated_image not in mines_locations:
                    incorrect_tiles.append(animated_image)

        for incorrect_flag in incorrect_tiles:
            if incorrect_flag in animated_images:
                animated_images.pop(incorrect_flag)

            # Drawing the X symbol to the screen as text, because there is no antialiasing for images. Without
            # it, the X image looks like crap because of jagged lines
            incorrect_flag_symbol = incorrect_flag_font.render("X", True, (255, 0, 0))
            incorrect_flag_symbol_rect = incorrect_flag_symbol.get_rect(
                center=(
                    (incorrect_flag[0]*x_box_size) + x_box_size/2,
                    (incorrect_flag[1]*y_box_size) + y_box_size/2
                )
            )
            gameboard.blit(incorrect_flag_symbol, incorrect_flag_symbol_rect)

        if mines_locations is not None:
            for mine in mines_locations:
                if mine in flipped_tiles:
                    gameboard.blit(mine_image, (mine[0] * x_box_size, mine[1] * y_box_size))

                hint_numbers_locations = []

                if mine[0] > 0 and mine[1] > 0:
                    hint_numbers_locations.append((mine[0]-1, mine[1]-1))
                if mine[1] > 0:
                    hint_numbers_locations.append((mine[0], mine[1]-1))
                if mine[0] < x_grid_size-1 and mine[1] > 0:
                    hint_numbers_locations.append((mine[0]+1, mine[1]-1))
                if mine[0] < x_grid_size-1:
                    hint_numbers_locations.append((mine[0]+1, mine[1]))
                if mine[0] < x_grid_size-1 and mine[1] < y_grid_size-1:
                    hint_numbers_locations.append((mine[0]+1, mine[1]+1))
                if mine[1] < y_grid_size-1:
                    hint_numbers_locations.append((mine[0], mine[1]+1))
                if mine[0] > 0 and mine[1] < y_grid_size-1:
                    hint_numbers_locations.append((mine[0]-1, mine[1]+1))
                if mine[0] > 0:
                    hint_numbers_locations.append((mine[0]-1, mine[1]))

                for hint_number in hint_numbers_locations:
                    if hint_number in flipped_tiles and hint_number not in mines_locations:
                        actual_hint_number = hint_numbers[hint_number[1]][hint_number[0]]

                        if actual_hint_number == 1:
                            color = (0, 100, 0)
                        elif actual_hint_number == 2:
                            color = (80, 80, 150)
                        elif actual_hint_number == 3:
                            color = (255, 0, 0)
                        else:
                            color = (255, 140, 0)

                        number      = hint_number_font.render(str(actual_hint_number), True, color)
                        number_rect = number.get_rect(
                            center=(
                                (hint_number[0]*x_box_size) + x_box_size/2,
                                (hint_number[1]*y_box_size) + y_box_size/2
                            )
                        )
                        gameboard.blit(number, number_rect)

        # Check that the mouse is on the gameboard and show the cursor "shadow"
        if not game_over:
            if 0 <= mouse_position_on_gameboard[0] < gameboard_size[0] \
                    and 0 <= mouse_position_on_gameboard[1] < gameboard_size[1]:

                gameboard.blit(
                    hover, (
                        int(mouse_position_on_gameboard[0] / x_box_size) * x_box_size,
                        int(mouse_position_on_gameboard[1] / y_box_size) * y_box_size
                    )
                )

        draw_grid(gameboard, x_grid_size, y_grid_size)

        # -------------------------------------------------

        # Better performance with just a rect instead of transparent surface as the shadow! (~ +5%)

        pygame.draw.rect(
            display, (0, 120, 0), (
                ((display_size[0] / 2) - (gameboard_size[0] / 2)) + (gameboard_size[0] / 2) * 0.1,
                ((display_size[1] / 2) - (gameboard_size[1] / 2)) + (gameboard_size[1] / 2) * 0.1,
                gameboard_size[0], gameboard_size[1]
            )
        )

        # Gameboard itself
        display.blit(gameboard, (
            display_size[0]/2 - gameboard_size[0]/2,
            display_size[1]/2 - gameboard_size[1]/2
        ))

        # Keyboard Events ---------------------------------

        for event in pygame.event.get():
            if event.type == pygame.QUIT:
                process_interrupted = True

            if event.type == pygame.MOUSEBUTTONDOWN:
                game_started = True if game_started is False else True

                if gameboard.get_rect().collidepoint(mouse_position_on_gameboard):
                    click_location = (
                        int(mouse_position_on_gameboard[0] / x_box_size),
                        int(mouse_position_on_gameboard[1] / y_box_size)
                    )

                    if event.button == 1:
                        # Generate mines after the first click to avoid losing instantly
                        if mines_locations is None:
                            # Avoid generating mines too close to the click location
                            tiles_to_avoid = [
                                (click_location[0], click_location[1]),      # The clicked tile
                                (click_location[0], click_location[1]-1),    # Top
                                (click_location[0]+1, click_location[1]-1),  # Top right
                                (click_location[0]+1, click_location[1]),    # Right
                                (click_location[0]+1, click_location[1]+1),  # Bottom right
                                (click_location[0], click_location[1]+1),    # Bottom
                                (click_location[0]-1, click_location[1]+1),  # Bottom left
                                (click_location[0]-1, click_location[1]),    # Left
                                (click_location[0]-1, click_location[1]-1),  # Top left
                            ]

                            mines_locations, hint_numbers = generate_mines(
                                amount_of_mines, x_grid_size, y_grid_size, tiles_to_avoid
                            )

                        if not game_over and click_location not in flagged_tiles and \
                                click_location not in flipped_tiles:

                            if click_location not in mines_locations and click_location not in flipped_tiles:
                                # Flip all the flippable tiles connected to the clicked tile
                                current_tile = (click_location[0], click_location[1])
                                path         = [current_tile]

                                flipped_tiles.append((current_tile[0], current_tile[1]))

                                while len(path) > 0:
                                    available_neighbours = []
                                    tiles_to_check       = [
                                        (current_tile[0], current_tile[1]-1),     # Top
                                        (current_tile[0]+1, current_tile[1]-1),   # Top right
                                        (current_tile[0]+1, current_tile[1]),     # Right
                                        (current_tile[0]+1, current_tile[1]+1),   # Bottom right
                                        (current_tile[0], current_tile[1]+1),     # Bottom
                                        (current_tile[0]-1, current_tile[1]+1),   # Bottom left
                                        (current_tile[0]-1, current_tile[1]),     # Left
                                        (current_tile[0]-1, current_tile[1]-1)    # Top left
                                    ]

                                    for tile in tiles_to_check:
                                        if 0 < tile[0]+1 < x_grid_size+1 and 0 < tile[1]+1 < y_grid_size+1:
                                            if hint_numbers[current_tile[1]][current_tile[0]] == 0:
                                                if tile not in flipped_tiles:
                                                    if tile not in flagged_tiles:
                                                        if tile not in mines_locations:
                                                            available_neighbours.append(tile)

                                    if len(available_neighbours) > 0:
                                        path.append(current_tile)
                                        current_tile = list(available_neighbours)[0]
                                        flipped_tiles.append(current_tile)
                                    else:
                                        current_tile = path[-1]
                                        path         = path[:-1]

                            else:
                                # TODO: GAME OVER! lost!
                                game_over = True

                                for mine_location in mines_locations:
                                    if mine_location not in flagged_tiles:
                                        flipped_tiles.append(mine_location)

                    if event.button == 3:
                        if not game_over and click_location not in flipped_tiles:
                            if click_location not in flagged_tiles:

                                animated_images[click_location] = AnimatedImage(
                                    int(click_location[0]), int(click_location[1]), flag_sprite
                                )

                                flagged_tiles.append(click_location)
                                amount_of_flags -= 1
                            else:
                                animated_images.pop(click_location)
                                flagged_tiles.pop(flagged_tiles.index(click_location))
                                amount_of_flags += 1

                            # Check if all the mines are flagged and if so, the game is over
                            if amount_of_flags == 0:
                                all_mines_flagged = True
                                for flagged_mine in mines_locations:
                                    if flagged_mine not in flagged_tiles:
                                        all_mines_flagged = False

                                if all_mines_flagged:
                                    # TODO: GAME OVER! Win!
                                    game_over = True

                                    # Save the new record in to a file
                                    if time_record is None or time < float(time_record):
                                        time_record = f"{time:.1f}"
                                        with open("minesweeper.save", "wb") as savefile:
                                            pickle.dump(time_record, savefile)
                                            savefile.close()

            if event.type == pygame.KEYDOWN:
                # Reset / Restart the game ----------------
                if event.key == pygame.K_RETURN:
                    game_started = game_over = False
                    time         = 0

                    amount_of_mines = amount_of_flags = const_amount_of_mines

                    # mines_locations and hint_numbers will be generated after the first click, to avoid losing
                    # the game instantly
                    mines_locations, hint_numbers = None, None

                    animated_images               = {}
                    # flagged_tiles = flipped_tiles = incorrect_tiles = [] <-- I literally have no idea,
                    # why this doesn't work, as it should do the same thing as the line below?
                    flagged_tiles, flipped_tiles, incorrect_tiles = [], [], []

        pygame.display.update()
        elapsed_time = clock.tick(0)

    pygame.quit()


if __name__ == "__main__":
    main()
