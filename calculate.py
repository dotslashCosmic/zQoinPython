a = 9999 # (lower is more coins, int 1-10000) Additive, base additive per block
b = 999 # (higher is more coins, int 1-100) Additive, Every b blocks, add e
c = 99 # (higher is more coins, int 1-100) Additive, Every c blocks, * d
d = 1.999 # (lower is more coins, float 1.0-10.0) Exponential multiplier
e = 99999 # (lower is more coins, int 1-1000000) How much to add every b blocks
base = 1e8 # Base difficulty
target = 1e12 # Maximum difficulty
# 1e8 = easy, 1e11 = medium, 1e14 = hard

def calculate_difficulty(index):
    base_difficulty = base + (coins * a) 
    additional_difficulty = (coins // b) * e
    exponential_difficulty = (coins // c) ** d
    difficulty = base_difficulty + additional_difficulty + exponential_difficulty
    return difficulty

print("Calculating number of zQoins...\nThis may take a while...")
coins = 0
base_p, target_p = int(base/1e8), int(target/1e8)
while True:
    if coins % 1e6 == 0:
        print(f"{(coins // 1e6) * 1} million zQoins", end='\r')
    difficulty = calculate_difficulty(coins)
    if difficulty >= target:
        break
    coins += 1
print(f"\nMax zQoins:", coins, "\nMinimum blockchain size:", int((280 + ((coins - 1)*484))/1048576), "mb", "\nApproximate days to mine @500H/s:", int(coins/43200), "\na:\t", a, "\nb:\t", b, "\nc:\t", c, "\nd:\t", d, "\ne:\t", e, "\nbase:\t", base, "\ntarget:\t", target, "\nDifficulty start:", base_p, "\nDifficulty end:  ", target_p)
