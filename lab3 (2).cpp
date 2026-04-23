#include <iostream>
#include <unistd.h>
#include <sched.h>
#include <ctime>
#include <fcntl.h>
#include <netdb.h>

using namespace std;

struct netent result_buf;
struct netent *result;

typedef struct
{
    int flag;
    char sym;
} targs;

int pipefd[2];

void* proc1(void* arg) {
    cout << "Поток 1 начал свою работу."  << endl;
    char buf[1024];
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        int h_errnop;
        int get_ = getnetent_r(&result_buf, buf, sizeof(buf), &result, &h_errnop);
        if (get_ != 0) {
            perror("netent_r error");
            pthread_exit((void*)111);
        }
        char* nname = result_buf.n_name;
        int k;
        for (ssize_t i = 1; nname[i-1] != '\0'; i++) {
            k = i;
        };
        //создать сообщение в буфере передачи count
        ssize_t nw = write(pipefd[1], &buf, k);
        if (nw == 0) {
            cout << "Сообщение пусто." << endl;
            break;
        }
        if (nw == -1) {
            perror("write error");
            pthread_exit((void*)11);
        }
        if (nw > 0) {
            cout << "Передано " << nw << "байт." << endl;
        }
        //fflush(stdout);
        sleep(1);
    }
    cout << "Поток 1 завершил свою работу." << endl;
    pthread_exit((void*)1);
}

void* proc2(void* arg) {
    cout << "Поток 2 начал свою работу."  << endl;
    char buf[1024];
    targs *args = (targs*) arg;
    while(args->flag == 0) {
        fflush(stdin);
        ssize_t nr = read(pipefd[0], &buf, sizeof(buf));
        if (nr == 0) {
            cout << "Достигнут конец файла." << endl;
            break;
        }
        if (nr == -1) {
            perror("read error");
            pthread_exit((void*)22);
        }
        if (nr > 0) {
            cout << "Прочитано:" << endl;
            cout << nr << endl;
            for (ssize_t i = 0; i < sizeof(buf); i++) {
                cout << buf[i];
            }
            cout << endl;
        }
    }
    cout << "Поток 2 завершил свою работу." << endl;
    pthread_exit((void*)2);
}
//int getnetent_r(struct netent *restrict result_buf, char *restrict buf,
//size_t buflen, struct netent **restrict result, int *restrict h_errnop);
//- получить структуру netent,
//из структуры выбрать поле, например, n_name, и его передавать
int main()
{
    cout << "Программа начала свою работу." << endl;

    targs arg1;
    targs arg2;

    arg1.flag = 0;
    arg1.sym = '1';
    arg2.flag = 0;
    arg2.sym = '2';

    int mode;

    pthread_t id1, id2;
    cout << "Введите режим работы программы:\n1 - pipe;\n2 - pipe2;\n3 - pipe + fcntl" << endl;
    cin >> mode;
    getchar();

    if (mode == 1) {
        int rv = pipe(pipefd);
        if (rv == -1) {
            perror("pipe error");
            return 8;
        }
    }
    if (mode == 2) {
        int rv = pipe2(pipefd, O_NONBLOCK);
        if (rv == -1) {
            perror("pipe2 error");
            return 12;
        }
    }
    if (mode == 3) {
        int rv = pipe(pipefd);
        if (rv == -1) {
            perror("pipe error");
            return 8;
        }
        if (fcntl(pipefd[0], F_SETFL, O_NONBLOCK) == -1) {
            perror("fcntl 0 error");
            return 13;
        }
        if (fcntl(pipefd[1], F_SETFL, O_NONBLOCK) == -1) {
            perror("fcntl 1 error");
            return 14;
        }
    }
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

    if (close(pipefd[0]) != 0) {
        perror("fd read error");
        return 9;
    }

    if (close(pipefd[1]) != 0) {
        perror("fd write error");
        return 7;
    }

    cout << "Программа завершила свою работу." << endl;
    return 0;
}
