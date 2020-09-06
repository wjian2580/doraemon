

def two(nums, target):
    dic = {}
    for num, index in enumerate(nums):
        if target - num in dic:
            return dic[target-num], index
        dic[num] = index


