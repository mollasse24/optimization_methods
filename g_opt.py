import numpy as np
import sqlite3
import random

DB_FILE_NAME = 'optimization_results.db'

def sphere_function(x):
    """1. Функция Сферы. Глобальный минимум f(0)=0."""
    return np.sum(x**2)

def rastrigin_function(x):
    """2. Функция Растригина. Глобальный минимум f(0)=0."""
    D = len(x)
    return 10 * D + np.sum(x**2 - 10 * np.cos(2 * np.pi * x))

def rosenbrock_function(x):
    """3. Функция Розенброка. Глобальный минимум f(1,1,...)=0."""
    # Используем срез [:-1] и [1:] для создания пар (xi, x(i+1))
    return np.sum(100.0 * (x[1:] - x[:-1]**2)**2 + (1 - x[:-1])**2)

def beale_function(x):
    """4. Функция Била. 2D функция. Глобальный минимум f(3, 0.5)=0."""
    if len(x) != 2:
        return np.inf
    x1, x2 = x[0], x[1]
    return (1.5 - x1 + x1*x2)**2 + (2.25 - x1 + x1*x2**2)**2 + (2.625 - x1 + x1*x2**3)**2

FUNCTIONS = {
    1: {'name': 'Сфера', 'func': sphere_function},
    2: {'name': 'Растригина', 'func': rastrigin_function},
    3: {'name': 'Розенброка', 'func': rosenbrock_function},
    4: {'name': 'Била', 'func': beale_function},
}

def init_db(db_name, algorithm_name):
    """Инициализирует базу данных и создает таблицу для конкретного алгоритма."""
    conn = sqlite3.connect(db_name)
    cursor = conn.cursor()  
  
    table_name = f"{algorithm_name.lower()}_iterations"
    
    cursor.execute(f"DROP TABLE IF EXISTS {table_name}")
    cursor.execute(f"""
        CREATE TABLE {table_name} (
            iteration INTEGER PRIMARY KEY,
            best_fitness REAL,
            best_solution TEXT,
            average_fitness REAL
        )
    """)
    conn.commit()
    return conn, cursor, table_name

def log_iteration(conn, cursor, table_name, iteration, best_fitness, best_solution, avg_fitness):
    """Записывает результаты итерации в базу данных."""
    # Преобразуем массив numpy в строку для хранения
    solution_str = np.array2string(best_solution, precision=6, separator=',')
    
    cursor.execute(f"""
        INSERT INTO {table_name} (iteration, best_fitness, best_solution, average_fitness)
        VALUES (?, ?, ?, ?)
    """, (iteration, best_fitness, solution_str, avg_fitness))
    conn.commit()

def pso_optimize(
    choice_num,
    db_name,
    pop_size=50,
    dim=3,
    iterations=150,
    bounds=(-5.12, 5.12),
    w=0.7, # Инерционный вес
    c1=2.0, # Коэффициент когнитивного обучения
    c2=2.0, # Коэффициент социального обучения
):
    
    algorithm_name = "PSO"
    db_conn, db_cursor, table_name = init_db(db_name, algorithm_name)
    
    # Проверка и выбор функции
    if choice_num not in FUNCTIONS:
        choice_num = 1
    function_info = FUNCTIONS[choice_num]
    objective_function = function_info['func']
    function_name = function_info['name']
    
    if function_name == 'Била':
        dim = 2
    
    print(f"\n--- Начинаем оптимизацию функции '{function_name}' с помощью {algorithm_name} (D={dim}) ---")
    print(f"Параметры: Итераций={iterations}, Рой={pop_size}, Границы={bounds}")
    
    # 1. Инициализация: Позиции (x) и Скорости (v)
    min_bound, max_bound = bounds
    positions = np.random.uniform(min_bound, max_bound, size=(pop_size, dim))
    # Инициализация скоростей небольшими случайными значениями
    velocities = np.random.uniform(-(max_bound - min_bound), (max_bound - min_bound), size=(pop_size, dim)) * 0.1 
    
    # 2. Инициализация лучшей личной позиции (pbest)
    pbest_positions = positions.copy()
    pbest_fitnesses = np.array([objective_function(p) for p in pbest_positions])
    
    # 3. Инициализация лучшей глобальной позиции (gbest)
    gbest_index = np.argmin(pbest_fitnesses)
    gbest_fitness = pbest_fitnesses[gbest_index]
    gbest_position = pbest_positions[gbest_index].copy()
    
    # 4. Цикл по итерациям
    for iteration in range(1, iterations + 1):
        
        # Обновление скоростей и позиций
        r1 = np.random.uniform(0, 1, size=(pop_size, dim))
        r2 = np.random.uniform(0, 1, size=(pop_size, dim))
        
        # Уравнение скорости: v_new = w*v + c1*r1*(pbest - x) + c2*r2*(gbest - x)
        cognitive_comp = c1 * r1 * (pbest_positions - positions)
        social_comp = c2 * r2 * (gbest_position - positions)
        
        velocities = w * velocities + cognitive_comp + social_comp        
     
        # vmax = 0.2 * (max_bound - min_bound)
        # velocities = np.clip(velocities, -vmax, vmax)
        
        positions += velocities
        
        # Ограничение позиций границами
        positions = np.clip(positions, min_bound, max_bound)
        
        # Оценка приспособленности
        current_fitnesses = np.array([objective_function(p) for p in positions])
        
        # Обновление pbest (лучшая личная позиция)
        mask = current_fitnesses < pbest_fitnesses
        pbest_fitnesses[mask] = current_fitnesses[mask]
        pbest_positions[mask] = positions[mask]
        
        # Обновление gbest (лучшая глобальная позиция)
        current_best_index = np.argmin(current_fitnesses)
        current_best_fitness = current_fitnesses[current_best_index]
        current_best_solution = positions[current_best_index]
        
        if current_best_fitness < gbest_fitness:
            gbest_fitness = current_best_fitness
            gbest_position = current_best_solution.copy()
            
        avg_fitness = np.mean(current_fitnesses)        
    
        log_iteration(
            db_conn, db_cursor, table_name, iteration,
            gbest_fitness, gbest_position, avg_fitness
        )
        
        if iteration % 25 == 0 or iteration == 1:
            print(f"Итерация {iteration}: Лучшее f(x) = {gbest_fitness:.6f}, Ср. f(x) = {avg_fitness:.6f}")
            
    db_conn.close()
    
    print("\n--- Оптимизация завершена ---")
    print(f"Алгоритм: {algorithm_name}, Функция: {function_name}")
    print(f"Глобальный минимум (f(x)): {gbest_fitness:.6f}")
    print(f"Точка минимума (x): {gbest_position}")
    print(f"Данные сохранены в файле '{db_name}' в таблице '{table_name}'")
    
    return gbest_position, gbest_fitness


def initialize_population(pop_size, dim, bounds):
    return np.random.uniform(bounds[0], bounds[1], size=(pop_size, dim))

def selection(population, fitnesses, num_parents):
    """Турнирный отбор (Tournament Selection)."""
    parents = np.empty((num_parents, population.shape[1]))
    tournament_size = 3
    for i in range(num_parents):
        indices = np.random.randint(0, len(population), tournament_size)
        tournament_fitnesses = fitnesses[indices]
        winner_index_in_tournament = np.argmin(tournament_fitnesses)  
        winner_index = indices[winner_index_in_tournament]
        parents[i, :] = population[winner_index, :]
    return parents

def crossover(parents, pop_size, bounds, pc):
    """Арифметическое скрещивание."""
    new_population = np.empty((pop_size, parents.shape[1]))
    num_parents = len(parents)
    
    for i in range(0, pop_size, 2):
        parent1_idx = i % num_parents
        parent2_idx = (i + 1) % num_parents
        
        if random.random() < pc:
            alpha = random.random()
            child1 = alpha * parents[parent1_idx] + (1 - alpha) * parents[parent2_idx]
            child2 = (1 - alpha) * parents[parent1_idx] + alpha * parents[parent2_idx]
            
            new_population[i, :] = child1
            if i + 1 < pop_size:
                new_population[i + 1, :] = child2
        else:
            new_population[i, :] = parents[parent1_idx]
            if i + 1 < pop_size:
                new_population[i + 1, :] = parents[parent2_idx]

    new_population = np.clip(new_population, bounds[0], bounds[1])
    return new_population

def mutation(population, bounds, pm, sigma):
    """Мутация по нормальному распределению (Gaussian Mutation)."""
    dim = population.shape[1]
    
    for i in range(population.shape[0]):
        for j in range(dim):
            if random.random() < pm:
                population[i, j] += np.random.normal(0, sigma)
                
    population = np.clip(population, bounds[0], bounds[1])
    return population

def genetic_algorithm_optimize(
    choice_num, 
    db_name, 
    pop_size=100, 
    dim=3, 
    generations=150, 
    bounds=(-5.12, 5.12),
    pc=0.8,
    pm=0.01,
    sigma=0.5
):
    
    algorithm_name = "GA"
    # 1. Инициализация DB
    db_conn, db_cursor, table_name = init_db(db_name, algorithm_name)
    
    # Проверка и выбор функции
    if choice_num not in FUNCTIONS:
        choice_num = 1
    
    function_info = FUNCTIONS[choice_num]
    objective_function = function_info['func']
    function_name = function_info['name']
    
    # Установка размерности для функции Била
    if function_name == 'Била':
        dim = 2

    print(f"\n--- Начинаем оптимизацию функции '{function_name}' с помощью {algorithm_name} (D={dim}) ---")
    print(f"Параметры: Поколений={generations}, Популяция={pop_size}, Границы={bounds}")
    
    # 2. Инициализация популяции
    population = initialize_population(pop_size, dim, bounds)
    best_overall_fitness = np.inf
    best_overall_solution = None
    
    # 3. Цикл по поколениям
    for generation in range(1, generations + 1):
        
        # Оценка приспособленности
        fitnesses = np.array([objective_function(individual) for individual in population])
        
        # Находим лучшее решение
        best_index = np.argmin(fitnesses)
        current_best_fitness = fitnesses[best_index]
        current_best_solution = population[best_index]
        
        # Обновляем лучшее общее решение
        if current_best_fitness < best_overall_fitness:
            best_overall_fitness = current_best_fitness
            best_overall_solution = current_best_solution
        
        avg_fitness = np.mean(fitnesses)
        
        # Логирование в БД
        log_iteration(
            db_conn, db_cursor, table_name, generation, 
            current_best_fitness, current_best_solution, avg_fitness
        )
        
        if generation % 25 == 0 or generation == 1:
            print(f"Поколение {generation}: Лучшее f(x) = {current_best_fitness:.6f}, Ср. f(x) = {avg_fitness:.6f}")
        
        # Отбор, Скрещивание, Мутация
        parents = selection(population, fitnesses, pop_size)
        new_population = crossover(parents, pop_size, bounds, pc)
        new_population = mutation(new_population, bounds, pm, sigma)
        
        # Элитизм (Сохранение лучшей особи)
        new_population[0] = best_overall_solution  
        
        population = new_population
        
    db_conn.close()
    
    print("\n--- Оптимизация завершена ---")
    print(f"Алгоритм: {algorithm_name}, Функция: {function_name}")
    print(f"Глобальный минимум (f(x)): {best_overall_fitness:.6f}")
    print(f"Точка минимума (x): {best_overall_solution}")
    print(f"Данные сохранены в файле '{db_name}' в таблице '{table_name}'") 
    
    return best_overall_solution, best_overall_fitness


# --- 7. Запуск программы (Обновлено для выбора алгоритма) ---

if __name__ == '__main__':
    
    print("--- Выбор алгоритма оптимизации ---")
    print("[1] - Генетический Алгоритм (GA)")
    print("[2] - Алгоритм Роя Частиц (PSO)")
    
    while True:
        try:
            algo_choice_input = input("\nВведите номер алгоритма (1 или 2): ")
            algo_choice = int(algo_choice_input)
            if algo_choice in [1, 2]:
                break
            else:
                print("Некорректный номер. Пожалуйста, введите 1 или 2.")
        except ValueError:
            print("Ошибка ввода. Пожалуйста, введите целое число.")
            
    print("\n--- Выбор функции для оптимизации ---")
    for num, info in FUNCTIONS.items():
        print(f"[{num}] - {info['name']}")
        
    while True:
        try:
            choice_input = input("\nВведите номер функции (1, 2, 3 или 4): ")
            choice = int(choice_input)
            if choice in FUNCTIONS:
                break
            else:
                print("Некорректный номер. Пожалуйста, введите число от 1 до 4.")
        except ValueError:
            print("Ошибка ввода. Пожалуйста, введите целое число.")

    # Запуск выбранного алгоритма
    if algo_choice == 1:
        # Запуск GA
        genetic_algorithm_optimize(
            choice_num=choice,
            db_name=DB_FILE_NAME,
        )
    elif algo_choice == 2:
        # Запуск PSO с некоторыми настройками по умолчанию
        pso_optimize(
            choice_num=choice,
            db_name=DB_FILE_NAME,
            pop_size=50,      # Меньше, чем для GA, обычно достаточно для PSO
            iterations=150,
            # Дополнительные параметры PSO
            w=0.729,
            c1=1.49445,
            c2=1.49445
        )
