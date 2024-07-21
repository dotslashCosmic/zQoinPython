def calculate_difficulty(index):
    a = 100 # (lower is more, int 1-1000) Additive
    b = 23 # (higher is more, int 1-10000) Additive
    c = 7 # (higher is more, int 1-10000) Additive
    d = 4 # (lower is more, float 1.0-10.0) Exponential-speed multiplier
    base_difficulty = base + (index * a) 
    additional_difficulty = 1 + ((index // b) + 10) * 1000
    exponential_difficulty = 1 + int((index // c) ** d)
    difficulty = base_difficulty + additional_difficulty + exponential_difficulty
    return difficulty

print("Calculating number of zQoins based on difficulty...\nThis may take a while...")
base = 1000000000 # Base difficulty
target_difficulty = 10000000000 # Maximum difficulty
index = 0 # Number of blocks on the blockchain
iterations = 0
while True:
    if index % 1000000 == 0:
        print(f"{(index // 1000000) * 1} million zQoins", end='\r')
    difficulty = calculate_difficulty(index)
    if difficulty >= target_difficulty:
        break
    index += 1
    iterations += 1
print(f"\nMax zQoins:", iterations, "\nMinimum blockchain size:", int((282 + ((iterations - 1)*179))/1024/1024), "mb", "\nApproximate days to mine @500H/s:", int(iterations*2/60/60/24), "\nBase difficulty:", base/100000000, "\nMax difficulty:", target_difficulty/100000000)