import sys
from random import *

sys.setrecursionlimit(10000)
count = 0
sudoku_temp = []
sudoku = []
sudoku_length = 9


def print_all():
    for row in range(len(sudoku)):
        for col in range(len(sudoku[row])):
            print(sudoku[row][col], end=' ')
        print()


# Fill 8*8 matrix with zeroes
for i in range(0, sudoku_length):
    sudoku_temp.append([])
    for j in range(0, sudoku_length):
        sudoku_temp[i].append(0)

sudoku = [row[:] for row in sudoku_temp]


def lists_intersection(list_of_lists):
    result = list(set.intersection(*map(set, list_of_lists)))
    return result


def get_digits_in_square(row, col):
    square_digits = []

    start_row = row - row % 3
    start_rol = col - col % 3

    for row in range(0, 3):
        for col in range(0, 3):
            if sudoku[row + start_row][col + start_rol]:
                square_digits.append(sudoku[row + start_row][col + start_rol])

    return square_digits


def generate():
    global count
    global sudoku
    global sudoku_temp
    count += 1

    err = False

    for row in range(0, sudoku_length):
        for col in range(0, sudoku_length):
            available_digits = check_available_digits(row, col)
            if not available_digits:
                err = True
                break
            else:
                rand_index = randint(0, len(available_digits) - 1)
                sudoku[row][col] = available_digits[rand_index]
        if err:
            break

    # if not available digits, copy sudoku_temp and started from beginning
    if err:
        sudoku = [row[:] for row in sudoku_temp]
        generate()
    else:
        print(f"Generated from {count} attempt")
        print_all()


def check_available_digits(row_index, col_index):
    intersect_list = []

    # check row
    row_available = check_available_service('row', row_index, col_index)
    intersect_list.append(row_available)

    # check col
    col_available = check_available_service('col', row_index, col_index)
    intersect_list.append(col_available)

    # check square
    square_available = check_available_service('square', row_index, col_index)
    intersect_list.append(square_available)

    available_digits = lists_intersection(intersect_list)

    return available_digits


# service function for check available digits
def check_available_service(check_type, row_index, col_index):
    allow_digits = []

    for row in range(1, sudoku_length + 1):
        allow_digits.append(row)

    if check_type == 'row':
        for num in sudoku[row_index]:
            if num:
                index_allow_digits = allow_digits.index(num)
                del allow_digits[index_allow_digits]

    elif check_type == 'col':
        column = []

        for row in range(0, len(sudoku)):
            for col in range(0, len(sudoku[row])):
                if col == col_index and sudoku[row][col]:
                    column.append(sudoku[row][col])

        for col_digit in column:
            index_allow_digits = allow_digits.index(col_digit)
            del allow_digits[index_allow_digits]

    elif check_type == 'square':
        digits_in_square = get_digits_in_square(row_index, col_index)
        for digit_in_square in digits_in_square:
            index_allow_digits = allow_digits.index(digit_in_square)
            del allow_digits[index_allow_digits]

    return allow_digits


generate()
