# Define the constants and variables
rho = 1.225  # Density of air in kg/m^3
v = 343      # Velocity of the object in m/s
A = 900       # Cross-sectional area of the object in m^2
C = 0.47        # Drag coefficient

# Compute drag using the formula Fdrag = 1/2 * rho * v^2 * A * C
Fdrag = 0.5 * rho * (v ** 2) * A * C

# Print the result
print(Fdrag)
