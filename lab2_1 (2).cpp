#include <iostream>
#include <unistd.h>
#include <pthread.h>
#include <sched.h>
#include <ctime>

using namespace std;

pthread_mutex_t mut;

typedef struct
{
    int flag;
    char sym;
} targs;

void* proc1(void* arg) {
    cout << "Поток 1 начал свою работу."  << endl;
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        if (pthread_mutex_lock(&mut) != 0) {
            perror("lock error");
            pthread_exit((void*)11);
        }
        cout << "Мьютекс захвачен потоком 1." << endl;
        for (int i = 0; i < 10; i++) {
            cout << args->sym << endl;
            fflush(stdout);
            sleep(1);
        }
        if (pthread_mutex_unlock(&mut) != 0) {
            perror("unlock error");
            pthread_exit((void*)111);
        }
        cout << "Мьютекс освобожден потоком 1." << endl;
        sleep(1);
    }

    cout << "Поток 1 завершил свою работу." << endl;
    pthread_exit((void*)1);
}

void* proc2(void* arg) {
    cout << "Поток 2 начал свою работу."  << endl;
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        if (pthread_mutex_lock(&mut) != 0) {
            perror("lock error");
            pthread_exit((void*)22);
        }
        cout << "Мьютекс захвачен потоком 2." << endl;
        for (int i = 0; i < 10; i++) {
            cout << args->sym << endl;
            fflush(stdout);
            sleep(1);
        }
        if (pthread_mutex_unlock(&mut) != 0) {
            perror("unlock error");
            pthread_exit((void*)222);
        }
        cout << "Мьютекс освобожден потоком 2." << endl;
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

    if (pthread_mutex_init(&mut, NULL) != 0) {
        perror("mutex create error");
        return 100;
    }
    cout << "Мьютекс инициализирован." << endl;

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

    if (pthread_mutex_destroy(&mut) != 0) {
        perror("destroy error");
        return 5;
    }
    cout << "Мьютекс удален." << endl;
    cout << "Программа завершила свою работу." << endl;
    return 0;
}
