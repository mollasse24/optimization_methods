#include <iostream>
#include <unistd.h>
#include <sched.h>
#include <ctime>
#include <fcntl.h>
#include <netdb.h>
#include <sys/wait.h>
#include <sys/types.h>
#include <bits/waitflags.h>

using namespace std;

//int execvpe(const char *file, char *const argv[], char *const envp[]).
int main(int argc, char* argv[])
{
    cout << "Программа 2 начала свою работу." << endl;

    int status;
    pid_t pid = fork();
    cout << "pid (p) " << getpid() << endl << "ppid (p) " << getppid << endl;
    if (pid == 0) {
        cout << "ppid (p) - " << getppid() << endl;
        int e = execvpe("./lab4", argv, environ);
        if (e == -1) {
            perror("exe error");
        }
    }
    else if (pid > 0) {
        cout << "pid (p)- " << getpid() << endl;
        while (int wp = waitpid(pid, &status, WNOHANG) == 0) {
            cout << "Ожидайте." << endl;
            sleep(1);
        }
        if (int wp = waitpid(pid, &status, WNOHANG) == -1) {
            perror("waitpid error");
            exit(4);
        }
        else if (int wp = waitpid(pid, &status, WNOHANG) != -1) cout << "Код завершения дочернего процесса - " << status << endl;
    }
    else {
        perror("fork");
    }

    cout << "Программа 2 завершила свою работу." << endl;
    exit(0);
}

