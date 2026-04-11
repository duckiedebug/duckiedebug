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

# Function to calculate the first law using the data from tb2
def first_law():
    v1, v2, v3 = None, None, None

    # Extract values from tb2
    for i in range(len(tb2) - 3):
        x1, t1 = tb2[i]
        x2, t2 = tb2[i + 1]
        x3, t3 = tb2[i + 2]
        x4, t4 = tb2[i + 3]

        v1 = (x2 - x1) / (t2 - t1)
        v2 = (x3 - x2) / (t3 - t2)
        v3 = (x4 - x3) / (t4 - t3)

    # Check if the velocities are equal
    if v1 == v2 == v3:
        a = "First Law proven."
    else:
        a = "First Law not proven."

    return a

# Function to populate tb with data points using the average_velocity() function
def data_table2():
    x, t = 0, 0
    dt = 1
    tb2 = [(x, t)]

    while t < t1:
        x += v * dt
        t += dt
        tb2.append((x, t))

    # Represent the tb2 as a table (list of tuples)
    tb3 = [(x, t) for x, t in tb2]
    return tb3


a = first_law()
print(a)

tb3 = data_table2()
print(tb3)
