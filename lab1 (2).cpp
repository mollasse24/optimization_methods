#include <iostream>
#include <unistd.h>
#include <sched.h>
#include <ctime>


using namespace std;

sched_param sch;

int _min_priority = sched_get_priority_min(SCHED_FIFO);
int _max_priority = sched_get_priority_max(SCHED_FIFO);


typedef struct
{
    int flag;
    char sym;
} targs;

void* proc1(void* arg) {
    cout << "Поток 1 начал свою работу."  << endl;
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        cout << args->sym << endl;
        fflush(stdout);
        sleep(1);
    }
    cout << "Поток 1 завершил свою работу." << endl;
    pthread_exit((void*)1);
}

void* proc2(void* arg) {
    cout << "Поток 2 начал свою работу."  << endl;
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        cout << args->sym << endl;
        fflush(stdout);
        sleep(1);
    }
    cout << "Поток 2 завершил свою работу." << endl;
    pthread_exit((void*)2);
}

int main()
{
    cout << "Программа начала свою работу." << endl;

    targs arg1;
    targs arg2;

    arg1.flag = 0;
    arg1.sym = '1';
    arg2.flag = 0;
    arg2.sym = '2';

    pthread_t id1, id2;

    //cout << _min_priority << "    " << _max_priority << endl;

    // существует 3 вида стратегии планирования: SCHED_FIFO, SCHED_RR, и SCHED_OTHER.
    // SCHED_FIFO - стратегия планирования, при которой первый поток выполняется до конца
    // SCHED_RR - стратегия циклического планирования, при которой каждый поток назначается процессору только в течение некоторого времени
    // SCHED_OTHER - стратегия планирования другого типа, для нового потока принимается по умолчанию (0)
    //будем использовать SCHED_FIFO

    //функция pthread_getschedparam позволяет через структуру sched_param получить приоритет планирования потока,
    //а функция pthread_setschedparam - поменять этот приоритет в диапазоне от минимально допустимого при данной стратегии до максимально (от _min_priority до _max_priority), то есть он будет выполняться с бОльшим приоритетом, нежели по умолчанию
    //при работе программы и выводе символов видно, что символ 2 выводится первее символа 1, а также поток 2 завершает работу раньше потока 1

    int policy = SCHED_FIFO;

    int param = pthread_getschedparam(id2, &policy, &sch);
    if (errno != 0) {
        perror("invalid get_param");
        return 16;
    }
    cout << "Параметр планирования потока 2 по умолчанию: " << sch.sched_priority << endl;

    sch.sched_priority = 10;
    param = pthread_setschedparam(id2, policy, &sch);
    if (errno != 0) {
        perror("invalid set_param");
        return 17;
    }
    cout << "Параметр планирования потока 2 после изменения: " << sch.sched_priority << endl;

    param = pthread_getschedparam(id2, &policy, &sch);
    if (errno != 0) {
        perror("invalid get_param");
        return 34;
    }
    cout << "Проверка изменения параметра планирования потока 2: " << sch.sched_priority << endl;


    if (pthread_create(&id1, NULL, proc1, &arg1) != 0) {
        perror("create 1 error");
        return 1;
    }
    if (pthread_create(&id2, NULL, proc2, &arg2) != 0) {
        perror("create 2 error");
        return 2;
    }

    cout << "Программа ждет нажатия клавиши." << endl;
    getchar();
    cout << "Клавиша нажата." << endl;

    arg1.flag = 1;
    arg2.flag = 1;

    int* exitcode;

    if (pthread_join(id1, (void**)&exitcode) != 0) {
        perror("join 1 error");
        return 3;
    }
    cout << "Поток 1 вернул значение." << "   exitcode = " << exitcode << endl;

    if (pthread_join(id2, (void**)&exitcode) != 0) {
        perror("join 2 error");
        return 4;
    }
    cout << "Поток 2 вернул значение." << "   exitcode = " << exitcode << endl;


    cout << "Программа завершила свою работу." << endl;
    return 0;
}
