#include <iostream>
#include <unistd.h>
#include <sched.h>
#include <ctime>
#include <fcntl.h>
#include <netdb.h>

using namespace std;

//int execvpe(const char *file, char *const argv[], char *const envp[]).
int main(int argc, char* argv[])
{
    cout << "Программа 1 начала свою работу." << endl;

    cout << "pid " << getpid() << endl << "ppid" << getppid() << endl;
    cout << "argv:" << endl;
    for (int i = 0; i < argc/*sizeof(argv)/sizeof(argv[0])*/; i++) {
        cout << argv[i] << endl;
        sleep(1);
    }
    cout << "envp: " << endl;
    for (int i = 0; i < argc/*sizeof(environ)/sizeof(environ[0])*/; i++) {
        cout << environ[i] << endl;
        sleep(1);
    }

    cout << "Программа 1 завершила свою работу." << endl;
    exit(10);
}

