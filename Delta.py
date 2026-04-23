# Constants
m0 = 549000    # Initial mass (kg)
pm0 = 488000   # Max propellant mass (kg)
br = 0.0049    # Burn rate per second
Ft = 7500000   # Thrust (N)
grav = 9.8     # Gravity (m/s^2)
dt = 10        # Time step (s)
tt = 160       # Total time (s)

# 1. Use a clear name for the list to avoid conflicts
flight_results = []

def run_simulation():
    # Use local variables for calculations
    current_m = m0
    current_v = 0.0

    # 2. Fixed the loop: range(start, stop, step)
    for t in range(0, tt + dt, dt):
        # Calculate current acceleration
        # (Thrust / current_mass) - gravity
        a = (Ft / current_m) - grav

        # Store current values in the list
        flight_results.append((t, current_m, current_v, a))

        # Update values for the next time step
        dm = current_m * br * dt
        current_m -= dm

        # Ensure mass doesn't drop below structural limits
        if current_m < (m0 - pm0):
            current_m = m0 - pm0

        current_v += (a * dt)

def display_results_table(data):
    # 3. Formatted header for better readability
    print(f"{'Time (s)':<10} {'Mass (kg)':<15} {'Velocity (m/s)':<15} {'Accel (m/s^2)':<15}")
    print("-" * 60)
    for t, m, v, a in data:
        print(f"{t:<10} {m:<15.2f} {v:<15.2f} {a:<15.2f}")

# Execute
run_simulation()
display_results_table(flight_results)
