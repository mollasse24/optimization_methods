#include <iostream>



using namespace std;

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
