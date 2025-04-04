# main_lizard.py
# -*- coding: utf-8 -*-

import os
import random as rd
import numpy as np
import matplotlib.pyplot as plt

###############################################################################
# 1) Microhabitat Classes
###############################################################################

class HabitatPatch:
    """
    Represents a small patch of habitat with its own temperature, moisture, etc.
    """

    def __init__(self, temp=25.0, moisture=0.5, shade=0.0):
        self.temp = temp      # e.g., °C
        self.moisture = moisture  # e.g., fraction or mm of water
        self.shade = shade    # fraction (0 = full sun, 1 = full shade)

    def update_conditions(self, day_time):
        """
        Example placeholder logic:
         - increase temperature slightly with day_time,
         - reduce moisture slightly, etc.
        """
        self.temp += 0.05 * (day_time / 24.0)
        self.moisture -= 0.01 * (day_time / 24.0)

        # Bound realistic values
        if self.temp < 0:
            self.temp = 0
        if self.moisture < 0:
            self.moisture = 0


class HabitatGrid:
    """
    2D grid of HabitatPatches, each with its own environmental conditions.
    """

    def __init__(self, rows=10, cols=10):
        self.rows = rows
        self.cols = cols
        self.grid = [
            [
                HabitatPatch(
                    temp=25.0 + rd.uniform(-2, 2),
                    moisture=0.5 + rd.uniform(-0.1, 0.1),
                    shade=rd.choice([0.0, 0.3, 0.7])
                )
                for _ in range(cols)
            ]
            for _ in range(rows)
        ]

    def update_all_patches(self, day_time):
        """
        Update each patch's conditions.  day_time can represent hours or days.
        """
        for r in range(self.rows):
            for c in range(self.cols):
                self.grid[r][c].update_conditions(day_time)

###############################################################################
# 2) Lizard Class (Spatially Explicit)
###############################################################################

class Lizard:
    population = []

    def __init__(self, age=0, row=0, col=0):
        """
        Each lizard has:
          - an age
          - a location (row, col)
          - a 'state' ("alive" or "dead")
          - fractional offspring remainder (offspring_remainder) from births
        """
        self.age = age
        self.row = row
        self.col = col
        self.state = 'alive'
        self.offspring_remainder = 0
        self.__class__.population.append(self)

    def move(self, habitat_grid):
        """
        Example movement: if temperature > 32°C,
        try to move to a neighboring patch that is cooler.
        """
        if self.state != 'alive':
            return

        current_patch = habitat_grid.grid[self.row][self.col]
        if current_patch.temp <= 32.0:
            # It's cool enough here; don't move.
            return

        # Otherwise, look among neighbors (3x3 area) for cooler temps
        neighbors = []
        for dr in [-1, 0, 1]:
            for dc in [-1, 0, 1]:
                nr = self.row + dr
                nc = self.col + dc
                if (0 <= nr < habitat_grid.rows) and (0 <= nc < habitat_grid.cols):
                    if not (nr == self.row and nc == self.col):
                        neighbors.append((nr, nc))

        # Find neighbor with the coolest temperature
        best_temp = current_patch.temp
        best_loc = (self.row, self.col)
        for (nr, nc) in neighbors:
            patch_temp = habitat_grid.grid[nr][nc].temp
            if patch_temp < best_temp:
                best_temp = patch_temp
                best_loc = (nr, nc)

        # Move if a cooler patch is found
        if best_loc != (self.row, self.col):
            self.row, self.col = best_loc

    def reproduce(self, bx, habitat_grid):
        """
        Offspring production depends on the local habitat's moisture (as an example).
        """
        if self.state != 'alive':
            return

        local_patch = habitat_grid.grid[self.row][self.col]
        dryness_factor = max(0.0, 1.0 - local_patch.moisture)
        # Suppose dryness can reduce births by up to 30%
        penalty = 1.0 - dryness_factor * 0.3

        # Base number of offspring from age-based bx
        base_offspring = bx[self.age] if self.age < len(bx) else 0.0
        actual_births = base_offspring * penalty

        # Accumulate fractional remainders
        self.offspring_remainder += (actual_births % 1)
        offspring_int = int(actual_births - (actual_births % 1))

        # If fractional remainder >=1, add 1 more baby
        if self.offspring_remainder >= 1:
            offspring_int += 1
            self.offspring_remainder -= 1

        # Create new lizards in the same patch
        for _ in range(offspring_int):
            Lizard(age=0, row=self.row, col=self.col)

    def survival(self, lx, habitat_grid):
        """
        Survival can depend on age-based lx and local temperature extremes.
        """
        if self.age == 0:
            # Age=0 lizards just born; we assume they survive this instant
            self.state = 'alive'
            return

        if self.age >= len(lx):
            # Past the maximum age index in lx => mortality
            self.state = 'dead'
            return

        # Basic age-based survival probability
        # e.g. probability = lx[age] / lx[age-1] if we interpret lx as "fraction alive by age"
        base_survival_prob = lx[self.age] / lx[self.age - 1] if self.age > 0 else lx[self.age]

        # Example: reduce survival further if local patch temp > 35°C
        patch_temp = habitat_grid.grid[self.row][self.col].temp
        if patch_temp > 35.0:
            base_survival_prob *= 0.8  # reduce by 20%

        # Roll the dice
        if np.random.uniform(0, 1) < base_survival_prob:
            self.state = 'alive'
        else:
            self.state = 'dead'

    def age_up(self):
        """
        Increase age by 1 each time step.
        If age grows too large (e.g. > some max), mortality sets in.
        """
        self.age += 1
        # Hard cutoff for demonstration (e.g. 15 years)
        if self.age > 15:
            self.state = 'dead'

###############################################################################
# 3) Driver Function to Run the Spatial IBM
###############################################################################

def run_spatial_ibm(num_steps=200, lx=None, bx=None, rows=10, cols=10):
    """
    Creates a HabitatGrid, populates it with lizards of various age classes,
    and simulates for num_steps. Returns a list of population sizes over time.
    """
    # 1) Create habitat
    habitat = HabitatGrid(rows=rows, cols=cols)

    # 2) Clear any previous population
    Lizard.population = []

    # 3) Initialize a sample age distribution of lizards across the grid
    #    (You'd fill in however many individuals you want in each age class.)
    #    Here, purely as an example:
    for age_class in range(len(lx)):
        # Suppose we add a small number of individuals for each age class
        n_initial = rd.randint(5, 15)
        for _ in range(n_initial):
            r = rd.randint(0, rows - 1)
            c = rd.randint(0, cols - 1)
            Lizard(age=age_class, row=r, col=c)

    # 4) Main time loop
    pop_sizes = []
    for step in range(num_steps):
        # Update habitat (day_time=step)
        habitat.update_all_patches(day_time=step)

        # Move, reproduce, survive
        for liz in Lizard.population:
            liz.move(habitat)
            liz.reproduce(bx, habitat)
            liz.survival(lx, habitat)

        # Age up
        for liz in Lizard.population:
            liz.age_up()

        # Remove any that died
        Lizard.population = [lz for lz in Lizard.population if lz.state == 'alive']

        # Track population size
        pop_sizes.append(len(Lizard.population))

    return pop_sizes

###############################################################################
# 4) Main Entry Point
###############################################################################

def main():
    """
    Main function: define parameters for the lizard, run the spatial IBM, plot results.
    """

    # -------------------------------------------------------------------------
    # 1) Example Lizard Life-History Parameters (Placeholder)
    #    Replace these with actual data for your species.
    #    Here, lx is "fraction surviving at each age index"
    #    and bx is "eggs laid per female at each age index".
    # -------------------------------------------------------------------------
    lizard_lx = [
        1.0,   # age=0 (birth) - by definition "alive fraction" = 1
        0.6,   # age=1
        0.4,   # age=2
        0.3,   # age=3
        0.2,   # age=4
        0.15,  # age=5
        0.10,  # age=6
        0.06,  # age=7
        0.02   # age=8 (almost all die by 8 for this hypothetical species)
    ]

    # Example annual fecundity (eggs/female) by age
    lizard_bx = [
        0,  # age=0 can't lay eggs
        2,  # age=1
        4,  # age=2
        5,  # age=3
        5,  # age=4
        4,  # age=5
        3,  # age=6
        1,  # age=7
        0   # age=8
    ]

    # -------------------------------------------------------------------------
    # 2) Run IBM
    # -------------------------------------------------------------------------
    num_steps = 50   # fewer time steps for demonstration
    rows = 10
    cols = 10

    pop_sizes = run_spatial_ibm(
        num_steps=num_steps,
        lx=lizard_lx,
        bx=lizard_bx,
        rows=rows,
        cols=cols
    )

    # -------------------------------------------------------------------------
    # 3) Plot the results
    # -------------------------------------------------------------------------
    plt.figure(figsize=(8, 5))
    plt.plot(pop_sizes, label="Spatial Lizard IBM")
    plt.xlabel("Time Step")
    plt.ylabel("Population Size")
    plt.title("Lizard Population Trajectory (Spatially Explicit IBM)")
    plt.legend()
    plt.tight_layout()

    # Optionally save figure
    desktop_path = os.path.expanduser("~/Desktop")
    plt.savefig(os.path.join(desktop_path, "lizard_ibm_population.png"), dpi=300)

    plt.show()


if __name__ == "__main__":
    main()
