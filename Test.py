
# Constants
d = 169000  # meters
t1 = 13      # seconds
py = 10000    # meters per second (initial velocity in the y direction)
pz = 20000   # meters per second (initial velocity in the z direction)

# Define a function to calculate average velocity
def average_velocity():
    v = d / t1
    return v

v = average_velocity()
print(v)

# Function to populate tb1 with data points using the average_velocity() function
def data_table1():
    x, t, dt = 0, 0, 1
    tb1 = []
    while t < t1:
        x += v * dt
        t += dt
        tb1.append((x, t))

    # Represent the tb1 as a table (list of tuples)
    tb2 = [(x, t) for x, t in tb1]
    return tb2

tb2 = data_table1()
print(tb2)
