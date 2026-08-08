"""
display config mod
"""
import pygame
from src.maze_loader import MazeLoader


class Display:

    def __init__(self, width: int = 800, height: int = 600) -> None:
        pygame.init()

        self.maze_loader = MazeLoader(width=28, height=31, seed=42)
        self.maze_data = self.maze_loader.get_maze_data()

        self.cell_size = 20

        screen_width = len(self.maze_data[0]) * self.cell_size
        screen_height = len(self.maze_data) * self.cell_size
        self.screen = pygame.display.set_mode((screen_width, screen_height))

        pygame.display.set_caption("Pac-Man")
        self.clock = pygame.time.Clock()

    def run(self) -> None:
        """
        main loop
        """
        running = True

        while running:

            for event in pygame.event.get():

                if event.type == pygame.QUIT:
                    running = False

            self.screen.fill((0, 0, 0))

            for y, row in enumerate(self.maze_data):
                for x, cell in enumerate(row):

                    if cell == 1:
                        rect = (
                            x * self.cell_size,
                            y * self.cell_size,
                            self.cell_size,
                            self.cell_size
                            )
                        pygame.draw.rect(self.screen, (0, 0, 255), rect)

            self.clock.tick(60)
            pygame.display.flip()

        pygame.quit()


if __name__ == "__main__":
    game_display = Display()
    game_display.run()
