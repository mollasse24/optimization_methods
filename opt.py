import numpy as np
import sqlite3
import csv
import json
from datetime import datetime
from typing import Dict, List, Tuple, Optional, Callable
import math

class OptimizationDatabase:
    def __init__(self, db_path: str = "optimization_experiments.db"):
        self.db_path = db_path
        self.init_database()
    
    def init_database(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Таблица экспериментов
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS experiments (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT,
                function_type TEXT,
                function_params TEXT,
                optimization_bounds TEXT,
                method_name TEXT,
                initial_point TEXT,
                initial_step REAL,
                target_accuracy REAL,
                computation_accuracy REAL,
                result_point TEXT,
                result_value REAL,
                iterations INTEGER,
                success BOOLEAN
            )
        ''')
        
        # Таблица итераций
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS iterations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                experiment_id INTEGER,
                iteration_number INTEGER,
                point_x REAL,
                point_y REAL,
                value REAL,
                step_size REAL,
                gradient_x REAL,
                gradient_y REAL,
                FOREIGN KEY (experiment_id) REFERENCES experiments (id)
            )
        ''')
        
        conn.commit()
        conn.close()
    
    def save_experiment(self, experiment_data: Dict, iterations: List[Dict]):
        """Сохранение эксперимента и его итераций"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Сохраняем основной эксперимент
        cursor.execute('''
            INSERT INTO experiments (
                timestamp, function_type, function_params, optimization_bounds,
                method_name, initial_point, initial_step, target_accuracy,
                computation_accuracy, result_point, result_value, iterations, success
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            experiment_data['timestamp'],
            experiment_data['function_type'],
            json.dumps(experiment_data['function_params']),
            json.dumps(experiment_data['optimization_bounds']),
            experiment_data['method_name'],
            json.dumps(experiment_data['initial_point']),
            experiment_data['initial_step'],
            experiment_data['target_accuracy'],
            experiment_data['computation_accuracy'],
            json.dumps(experiment_data['result_point']),
            experiment_data['result_value'],
            experiment_data['iterations'],
            experiment_data['success']
        ))
        
        experiment_id = cursor.lastrowid
        
        # Сохраняем итерации
        for iter_data in iterations:
            cursor.execute('''
                INSERT INTO iterations (
                    experiment_id, iteration_number, point_x, point_y,
                    value, step_size, gradient_x, gradient_y
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            ''', (
                experiment_id,
                iter_data['iteration_number'],
                iter_data['point_x'],
                iter_data['point_y'],
                iter_data['value'],
                iter_data.get('step_size', 0.0),
                iter_data.get('gradient_x', 0.0),
                iter_data.get('gradient_y', 0.0)
            ))
        
        conn.commit()
        conn.close()
    
    def export_to_csv(self, filename: str = "optimization_results.csv"):
        """Экспорт результатов в CSV"""
        conn = sqlite3.connect(self.db_path)
        
        # Основные результаты экспериментов
        experiments_df = pd.read_sql_query('''
            SELECT e.*, 
                   COUNT(i.id) as total_iterations
            FROM experiments e
            LEFT JOIN iterations i ON e.id = i.experiment_id
            GROUP BY e.id
        ''', conn)
        
        experiments_df.to_csv(f"experiments_{filename}", index=False)
        
        # Детальные итерации
        iterations_df = pd.read_sql_query('''
            SELECT e.method_name, e.function_type, i.*
            FROM iterations i
            JOIN experiments e ON i.experiment_id = e.id
        ''', conn)
        
        iterations_df.to_csv(f"iterations_{filename}", index=False)
        
        conn.close()

class TestFunctions:
    """Класс тестовых функций"""
    
    @staticmethod
    def quadratic_form(x: np.ndarray, params: Dict) -> float:
        """Квадратичная форма: f(x,y) = a*x² + b*y² + c*x*y + d*x + e*y + f"""
        a, b, c, d, e, f = params['coefficients']
        x_val, y_val = x
        return a*x_val**2 + b*y_val**2 + c*x_val*y_val + d*x_val + e*y_val + f
    
    @staticmethod
    def exponential_trigonometric(x: np.ndarray, params: Dict) -> float:
        """Экспоненциально-тригонометрическая функция: f(x,y) = e^(a*x) * sin(b*y)"""
        a, b = params['coefficients']
        x_val, y_val = x
        if params.get('use_cos', False):
            return math.exp(a * x_val) * math.cos(b * y_val)
        else:
            return math.exp(a * x_val) * math.sin(b * y_val)
    
    @staticmethod
    def rosenbrock(x: np.ndarray, params: Dict) -> float:
        """Функция Розенброка: f(x,y) = (a - x)² + b*(y - x²)²"""
        a, b = params['coefficients']
        x_val, y_val = x
        return (a - x_val)**2 + b * (y_val - x_val**2)**2
    
    @staticmethod
    def get_gradient(func: Callable, x: np.ndarray, params: Dict, epsilon: float = 1e-8) -> np.ndarray:
        """Численное вычисление градиента"""
        grad = np.zeros_like(x)
        for i in range(len(x)):
            x_plus = x.copy()
            x_minus = x.copy()
            x_plus[i] += epsilon
            x_minus[i] -= epsilon
            grad[i] = (func(x_plus, params) - func(x_minus, params)) / (2 * epsilon)
        return grad

class OptimizationMethods:
    """Класс методов оптимизации с исправлениями на основе документации"""
    
    def __init__(self, db: OptimizationDatabase):
        self.db = db
        self.functions = TestFunctions()
    
    def coordinate_descent_basic(self, func: Callable, params: Dict, initial_point: np.ndarray,
                               initial_step: float, target_accuracy: float, computation_accuracy: float,
                               bounds: List[Tuple[float, float]], max_iterations: int = 1000) -> Tuple[np.ndarray, List[Dict]]:
        """Базовый метод покоординатного спуска (фиксированный шаг)"""
        current_point = initial_point.copy()
        step = initial_step
        iterations_data = []
        prev_value = float('inf')
        
        for iteration in range(max_iterations):
            current_value = func(current_point, params)
            
            # Сохраняем данные итерации
            grad = self.functions.get_gradient(func, current_point, params, computation_accuracy)
            iterations_data.append({
                'iteration_number': iteration,
                'point_x': current_point[0],
                'point_y': current_point[1],
                'value': current_value,
                'step_size': step,
                'gradient_x': grad[0],
                'gradient_y': grad[1]
            })
            
            # Проверка сходимости (по изменению значения функции)
            if iteration > 0 and abs(current_value - prev_value) < target_accuracy:
                break
            
            prev_value = current_value
            
            # Поочередная оптимизация по координатам
            for coord in range(len(current_point)):
                # Пробуем шаг вперед
                point_forward = current_point.copy()
                point_forward[coord] += step
                if self._is_in_bounds(point_forward, bounds):
                    value_forward = func(point_forward, params)
                else:
                    value_forward = float('inf')
                
                # Пробуем шаг назад
                point_backward = current_point.copy()
                point_backward[coord] -= step
                if self._is_in_bounds(point_backward, bounds):
                    value_backward = func(point_backward, params)
                else:
                    value_backward = float('inf')
                
                # Выбираем наилучшее направление
                if value_forward < current_value:
                    current_point = point_forward
                    current_value = value_forward
                elif value_backward < current_value:
                    current_point = point_backward
                    current_value = value_backward
            
            # Адаптация шага (дробление шага при отсутствии улучшения)
            if iteration > 0:
                step *= 0.95  # Постепенное уменьшение шага
        
        return current_point, iterations_data
    
    def coordinate_descent_steepest(self, func: Callable, params: Dict, initial_point: np.ndarray,
                                  initial_step: float, target_accuracy: float, computation_accuracy: float,
                                  bounds: List[Tuple[float, float]], max_iterations: int = 1000) -> Tuple[np.ndarray, List[Dict]]:
        """Метод покоординатного спуска с наискорейшим спуском"""
        current_point = initial_point.copy()
        iterations_data = []
        prev_value = float('inf')
        
        for iteration in range(max_iterations):
            current_value = func(current_point, params)
            
            # Сохраняем данные итерации
            grad = self.functions.get_gradient(func, current_point, params, computation_accuracy)
            iterations_data.append({
                'iteration_number': iteration,
                'point_x': current_point[0],
                'point_y': current_point[1],
                'value': current_value,
                'step_size': 0.0,  # Будет определен в line search
                'gradient_x': grad[0],
                'gradient_y': grad[1]
            })
            
            # Проверка сходимости
            if iteration > 0 and abs(current_value - prev_value) < target_accuracy:
                break
            
            prev_value = current_value
            
            # Поочередная оптимизация по координатам с подбором шага
            for coord in range(len(current_point)):
                # Создаем направление для текущей координаты
                direction = np.zeros_like(current_point)
                direction[coord] = 1.0  # Направление вдоль координаты
                
                # Ищем оптимальный шаг методом наискорейшего спуска
                optimal_step, found_improvement = self._one_dimensional_search(
                    func, params, current_point, direction, bounds, initial_step, current_value
                )
                
                if found_improvement:
                    # Обновляем точку с оптимальным шагом
                    new_point = current_point.copy()
                    new_point[coord] += optimal_step
                    if self._is_in_bounds(new_point, bounds):
                        new_value = func(new_point, params)
                        if new_value < current_value:
                            current_point = new_point
                            current_value = new_value
                
                # Также проверяем движение в обратном направлении
                direction[coord] = -1.0
                optimal_step, found_improvement = self._one_dimensional_search(
                    func, params, current_point, direction, bounds, initial_step, current_value
                )
                
                if found_improvement:
                    new_point = current_point.copy()
                    new_point[coord] -= optimal_step
                    if self._is_in_bounds(new_point, bounds):
                        new_value = func(new_point, params)
                        if new_value < current_value:
                            current_point = new_point
                            current_value = new_value
        
        return current_point, iterations_data
    
    def gradient_descent_basic(self, func: Callable, params: Dict, initial_point: np.ndarray,
                             initial_step: float, target_accuracy: float, computation_accuracy: float,
                             bounds: List[Tuple[float, float]], max_iterations: int = 1000) -> Tuple[np.ndarray, List[Dict]]:
        """Базовый метод градиентного спуска с дроблением шага"""
        current_point = initial_point.copy()
        step = initial_step
        iterations_data = []
        
        for iteration in range(max_iterations):
            current_value = func(current_point, params)
            grad = self.functions.get_gradient(func, current_point, params, computation_accuracy)
            
            # Сохраняем данные итерации
            iterations_data.append({
                'iteration_number': iteration,
                'point_x': current_point[0],
                'point_y': current_point[1],
                'value': current_value,
                'step_size': step,
                'gradient_x': grad[0],
                'gradient_y': grad[1]
            })
            
            # Проверка сходимости по норме градиента
            if np.linalg.norm(grad) < target_accuracy:
                break
            
            # Движение против градиента
            new_point = current_point - step * grad
            
            # Проверка границ
            if not self._is_in_bounds(new_point, bounds):
                # Проекция на границы
                for i in range(len(new_point)):
                    new_point[i] = max(bounds[i][0], min(bounds[i][1], new_point[i]))
            
            new_value = func(new_point, params)
            
            # Дробление шага при отсутствии улучшения (как в документации)
            if new_value < current_value:
                current_point = new_point
                # Можно немного увеличить шаг при успехе
                step *= 1.05
            else:
                # Дробление шага при неудаче
                step *= 0.5
            
            # Ограничение шага снизу
            step = max(step, 1e-10)
        
        return current_point, iterations_data
    
    def gradient_descent_ravine(self, func: Callable, params: Dict, initial_point: np.ndarray,
                              initial_step: float, target_accuracy: float, computation_accuracy: float,
                              bounds: List[Tuple[float, float]], max_iterations: int = 1000) -> Tuple[np.ndarray, List[Dict]]:
        """Метод градиентного спуска с овражным методом адаптации шага"""
        current_point = initial_point.copy()
        step = initial_step
        iterations_data = []
        prev_grad = None
        ravine_detected = False
        ravine_counter = 0
        
        for iteration in range(max_iterations):
            current_value = func(current_point, params)
            grad = self.functions.get_gradient(func, current_point, params, computation_accuracy)
            
            # Сохраняем данные итерации
            iterations_data.append({
                'iteration_number': iteration,
                'point_x': current_point[0],
                'point_y': current_point[1],
                'value': current_value,
                'step_size': step,
                'gradient_x': grad[0],
                'gradient_y': grad[1],
                'ravine_detected': ravine_detected
            })
            
            # Проверка сходимости
            if np.linalg.norm(grad) < target_accuracy:
                break
            
            # Овражный метод: анализ изменения градиента
            if prev_grad is not None:
                grad_change = np.linalg.norm(grad - prev_grad)
                angle_change = self._angle_between_vectors(grad, prev_grad)
                
                # Обнаружение оврага (резкое изменение направления)
                if angle_change > 0.5:  # Угол больше ~30 градусов
                    ravine_detected = True
                    ravine_counter = 5  # Держим увеличенный шаг несколько итераций
                    step *= 1.5  # Увеличиваем шаг для быстрого прохождения оврага
                else:
                    ravine_detected = False
                    if ravine_counter > 0:
                        ravine_counter -= 1
                    else:
                        step *= 0.9  # Постепенно уменьшаем шаг на пологих участках
            
            # Движение против градиента
            new_point = current_point - step * grad
            
            # Проверка границ
            if not self._is_in_bounds(new_point, bounds):
                for i in range(len(new_point)):
                    new_point[i] = max(bounds[i][0], min(bounds[i][1], new_point[i]))
            
            new_value = func(new_point, params)
            
            # Проверка улучшения
            if new_value < current_value:
                current_point = new_point
            else:
                # Если нет улучшения, уменьшаем шаг
                step *= 0.7
            
            # Ограничения на шаг
            step = max(step, 1e-10)
            step = min(step, 10.0)  # Верхнее ограничение
            
            prev_grad = grad.copy()
        
        return current_point, iterations_data
    
    def _one_dimensional_search(self, func: Callable, params: Dict, point: np.ndarray, 
                               direction: np.ndarray, bounds: List[Tuple[float, float]], 
                               initial_step: float, current_value: float) -> Tuple[float, bool]:
        """Одномерный поиск оптимального шага вдоль направления"""
        best_step = 0.0
        best_value = current_value
        found_improvement = False
        
        # Тестируем различные шаги (сканирование до первого минимума)
        test_steps = [0.1, 0.5, 1.0, 1.5, 2.0, 3.0, 5.0]
        
        for step_mult in test_steps:
            test_step = initial_step * step_mult
            test_point = point + test_step * direction
            
            if self._is_in_bounds(test_point, bounds):
                test_value = func(test_point, params)
                
                if test_value < best_value:
                    best_value = test_value
                    best_step = test_step
                    found_improvement = True
                else:
                    # Если значение начало ухудшаться, останавливаемся
                    break
        
        return best_step, found_improvement
    
    def _angle_between_vectors(self, v1: np.ndarray, v2: np.ndarray) -> float:
        """Вычисление угла между векторами в радианах"""
        if np.linalg.norm(v1) == 0 or np.linalg.norm(v2) == 0:
            return 0.0
        
        cos_angle = np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))
        cos_angle = np.clip(cos_angle, -1.0, 1.0)  # Избегаем численных ошибок
        return math.acos(cos_angle)
    
    def _is_in_bounds(self, point: np.ndarray, bounds: List[Tuple[float, float]]) -> bool:
        """Проверка нахождения точки в допустимой области"""
        for i, coord in enumerate(point):
            if coord < bounds[i][0] or coord > bounds[i][1]:
                return False
        return True

class ExperimentRunner:
    """Класс для проведения вычислительных экспериментов"""
    
    def __init__(self):
        self.db = OptimizationDatabase()
        self.optimizer = OptimizationMethods(self.db)
        self.function_map = {
            'quadratic': self.optimizer.functions.quadratic_form,
            'exponential_trig': self.optimizer.functions.exponential_trigonometric,
            'rosenbrock': self.optimizer.functions.rosenbrock
        }
    
    def run_comprehensive_experiment(self):
        """Проведение комплексного эксперимента"""
        print("=== ВЫЧИСЛИТЕЛЬНЫЙ ЭКСПЕРИМЕНТ ПО ОПТИМИЗАЦИИ ===")
        
        # Базовые параметры
        base_configs = self._get_base_configurations()
        
        for func_name, base_config in base_configs.items():
            print(f"\n--- Тестирование функции: {func_name} ---")
            
            # Вариации параметров
            variations = self._generate_variations(base_config)
            
            for i, variation in enumerate(variations[:3]):  # Первые 3 вариации
                print(f"Вариация {i+1}: {variation['description']}")
                
                # Запуск методов оптимизации
                self._run_methods_for_variation(func_name, variation)
    
    def _get_base_configurations(self) -> Dict:
        """Базовые конфигурации тестовых функций"""
        return {
            'quadratic': {
                'function_params': {'coefficients': [1.0, 2.0, 0.5, -1.0, -2.0, 3.0]},
                'bounds': [(-10, 10), (-10, 10)],
                'initial_point': [5.0, 5.0],
                'initial_step': 0.1,
                'target_accuracy': 1e-6,
                'computation_accuracy': 1e-8
            },
            'exponential_trig': {
                'function_params': {'coefficients': [0.5, 2.0], 'use_cos': False},
                'bounds': [(-5, 5), (-5, 5)],
                'initial_point': [2.0, 2.0],
                'initial_step': 0.05,
                'target_accuracy': 1e-6,
                'computation_accuracy': 1e-8
            },
            'rosenbrock': {
                'function_params': {'coefficients': [1.0, 100.0]},  # Классические параметры
                'bounds': [(-2, 2), (-1, 3)],
                'initial_point': [-1.5, 2.0],
                'initial_step': 0.01,
                'target_accuracy': 1e-6,
                'computation_accuracy': 1e-8
            }
        }
    
    def _generate_variations(self, base_config: Dict) -> List[Dict]:
        """Генерация вариаций параметров"""
        variations = []
        
        # Вариации параметров функции
        if 'coefficients' in base_config['function_params']:
            coeff_variations = [
                [c * 2 for c in base_config['function_params']['coefficients']],
                [c * 0.5 for c in base_config['function_params']['coefficients']],
                [c * (-1) for c in base_config['function_params']['coefficients']]
            ]
            for i, coeffs in enumerate(coeff_variations):
                variation = base_config.copy()
                variation['function_params'] = variation['function_params'].copy()
                variation['function_params']['coefficients'] = coeffs
                variation['description'] = f"Коэффициенты функции × {2 if i==0 else 0.5 if i==1 else -1}"
                variations.append(variation)
        
        # Вариации начального приближения
        initial_points = [
            [base_config['initial_point'][0] + 2, base_config['initial_point'][1] + 2],
            [base_config['initial_point'][0] - 2, base_config['initial_point'][1] - 2],
            [base_config['initial_point'][0] * (-1), base_config['initial_point'][1] * (-1)]
        ]
        for i, point in enumerate(initial_points):
            variation = base_config.copy()
            variation['initial_point'] = point
            variation['description'] = f"Начальное приближение {i+1}"
            variations.append(variation)
        
        # Вариации начального шага
        steps = [base_config['initial_step'] * 2, base_config['initial_step'] * 0.5, base_config['initial_step'] * 10]
        for i, step in enumerate(steps):
            variation = base_config.copy()
            variation['initial_step'] = step
            variation['description'] = f"Начальный шаг × {2 if i==0 else 0.5 if i==1 else 10}"
            variations.append(variation)
        
        # Вариации точности
        accuracies = [1e-4, 1e-8, 1e-10]
        for i, acc in enumerate(accuracies):
            variation = base_config.copy()
            variation['target_accuracy'] = acc
            variation['description'] = f"Точность решения {acc}"
            variations.append(variation)
        
        # Вариации точности вычислений
        comp_accuracies = [1e-6, 1e-10, 1e-12]
        for i, comp_acc in enumerate(comp_accuracies):
            variation = base_config.copy()
            variation['computation_accuracy'] = comp_acc
            variation['description'] = f"Точность вычислений {comp_acc}"
            variations.append(variation)
        
        return variations
    
    def _run_methods_for_variation(self, func_name: str, config: Dict):
        """Запуск всех методов для данной вариации"""
        func = self.function_map[func_name]
        
        # 4 метода согласно требованиям - ИСПРАВЛЕННЫЕ ИМЕНА МЕТОДОВ
        methods = [
            ('coordinate_basic', 'Покоординатный спуск (базовый)', self.optimizer.coordinate_descent_basic),
            ('coordinate_steepest', 'Покоординатный спуск с наискорейшим спуском', self.optimizer.coordinate_descent_steepest),
            ('gradient_basic', 'Градиентный спуск (базовый)', self.optimizer.gradient_descent_basic),
            ('gradient_ravine', 'Градиентный спуск с овражным методом', self.optimizer.gradient_descent_ravine)
        ]
        
        for method_key, method_name, method_func in methods:
            try:
                result, iterations = method_func(
                    func, config['function_params'], 
                    np.array(config['initial_point']), config['initial_step'],
                    config['target_accuracy'], config['computation_accuracy'],
                    config['bounds']
                )
                
                # Сохранение результатов
                experiment_data = {
                    'timestamp': datetime.now().isoformat(),
                    'function_type': func_name,
                    'function_params': config['function_params'],
                    'optimization_bounds': config['bounds'],
                    'method_name': method_name,
                    'initial_point': config['initial_point'],
                    'initial_step': config['initial_step'],
                    'target_accuracy': config['target_accuracy'],
                    'computation_accuracy': config['computation_accuracy'],
                    'result_point': result.tolist(),
                    'result_value': float(func(result, config['function_params'])),
                    'iterations': len(iterations),
                    'success': True
                }
                
                self.db.save_experiment(experiment_data, iterations)
                print(f"  {method_name}: {len(iterations)} итераций, результат: {result}, значение: {experiment_data['result_value']:.6f}")
                
            except Exception as e:
                print(f"  Ошибка в {method_name}: {e}")
    
    def run_custom_experiment(self):
        """Запуск пользовательского эксперимента"""
        print("\n=== ПОЛЬЗОВАТЕЛЬСКИЙ ЭКСПЕРИМЕНТ ===")
        
        # Выбор функции
        print("Выберите целевую функцию:")
        print("1. Квадратичная форма")
        print("2. Экспоненциально-тригонометрическая")
        print("3. Функция Розенброка")
        
        choice = input("Введите номер (1-3): ").strip()
        function_choice = {
            '1': 'quadratic',
            '2': 'exponential_trig', 
            '3': 'rosenbrock'
        }.get(choice, 'quadratic')
        
        # Ввод параметров
        config = self._get_user_input(function_choice)
        
        # Запуск
        self._run_methods_for_variation(function_choice, config)

    def _get_user_input(self, function_type: str) -> Dict:
        """Получение параметров от пользователя"""
        config = {}
        
        print("\nВведите параметры функции:")
        if function_type == 'quadratic':
            print("Коэффициенты квадратичной формы: a*x² + b*y² + c*x*y + d*x + e*y + f")
            coeffs = []
            for coef_name in ['a', 'b', 'c', 'd', 'e', 'f']:
                coeffs.append(float(input(f"{coef_name} = ")))
            config['function_params'] = {'coefficients': coeffs}
        
        elif function_type == 'exponential_trig':
            a = float(input("Коэффициент экспоненты a (в e^(a*x)): "))
            b = float(input("Коэффициент тригонометрической функции b (в sin(b*y) или cos(b*y)): "))
            use_cos = input("Использовать cos вместо sin? (y/n): ").lower() == 'y'
            config['function_params'] = {'coefficients': [a, b], 'use_cos': use_cos}
        
        elif function_type == 'rosenbrock':
            a = float(input("Параметр a (в (a-x)²): ") or "1.0")
            b = float(input("Параметр b (в b*(y-x²)²): ") or "100.0")
            config['function_params'] = {'coefficients': [a, b]}
        
        print("\nВведите границы оптимизации:")
        x_min = float(input("Минимум x: ") or "-10")
        x_max = float(input("Максимум x: ") or "10")
        y_min = float(input("Минимум y: ") or "-10")
        y_max = float(input("Максимум y: ") or "10")
        config['bounds'] = [(x_min, x_max), (y_min, y_max)]
        
        print("\nВведите начальное приближение:")
        x0 = float(input("x0: ") or "0")
        y0 = float(input("y0: ") or "0")
        config['initial_point'] = [x0, y0]
        
        config['initial_step'] = float(input("Начальный шаг: ") or "0.1")
        config['target_accuracy'] = float(input("Точность решения: ") or "1e-6")
        config['computation_accuracy'] = float(input("Точность вычислений: ") or "1e-8")
        
        return config

def main():
    """Основная функция"""
    runner = ExperimentRunner()
    
    while True:
        print("\n" + "="*50)
        print("СИСТЕМА ЭКСПЕРИМЕНТОВ ПО ОПТИМИЗАЦИИ")
        print("="*50)
        print("1. Запустить комплексный эксперимент")
        print("2. Запустить пользовательский эксперимент")
        print("3. Экспорт результатов в CSV")
        print("4. Выход")
        
        choice = input("Выберите действие (1-4): ").strip()
        
        if choice == '1':
            runner.run_comprehensive_experiment()
        elif choice == '2':
            runner.run_custom_experiment()
        elif choice == '3':
            runner.db.export_to_csv()
            print("Результаты экспортированы в CSV")
        elif choice == '4':
            print("Завершение работы...")
            break
        else:
            print("Неверный выбор!")

if __name__ == "__main__":
    # Необходимый импорт для экспорта
    import pandas as pd
    main()