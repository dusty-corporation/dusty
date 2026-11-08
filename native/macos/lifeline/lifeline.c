/*
 * dusty-lifeline: run one Dusty processing program and make sure it and every
 * program it starts die when the app cancels, times out or goes away (ADR 0037).
 *
 * Usage: dusty-lifeline <control-fd> <absolute-target> [target arguments...]
 *
 * The app keeps the write end of a pipe whose read end is <control-fd> and never
 * writes to it. The pipe is the only command channel. When it becomes readable
 * (end of file because the app closed it on cancel or timeout, or because the
 * app died, including by SIGKILL), the helper kills the target's process group
 * with SIGKILL, reaps the target and exits with EXIT_CANCELLED.
 *
 * The helper leads its own process group, apart from the app. The target is
 * started as the leader of a second new group, so one killpg call removes the
 * target and all of its descendants while the helper stays alive to reap the
 * target and report the result. The target's group is killed while the target
 * is still an unreaped zombie, so its process ID cannot have been reused.
 *
 * Exit codes: the target's own exit code, 128 + N when the target was killed
 * by signal N, EXIT_CANCELLED on cancel, 126 when the target could not be
 * executed, 127 when it does not exist and EXIT_SETUP when the helper itself
 * could not start. The helper prints nothing, so it never echoes paths.
 */

#include <errno.h>
#include <fcntl.h>
#include <signal.h>
#include <stdlib.h>
#include <sys/event.h>
#include <sys/types.h>
#include <sys/wait.h>
#include <unistd.h>

#define EXIT_SETUP 124
#define EXIT_CANCELLED 125

/* The target gets exactly the helper's own environment. The app builds that
 * environment explicitly for each launch and passes it to posix_spawn, so the
 * helper never adds, removes or inherits anything else (ADR 0037). */
extern char **environ;

/* Requests to stop the helper itself are treated like a cancel, so that a
 * polite kill of the helper never leaves the target running unsupervised. */
static const int stop_signals[] = {SIGHUP, SIGINT, SIGTERM};
#define STOP_SIGNAL_COUNT (sizeof(stop_signals) / sizeof(stop_signals[0]))

static int parse_fd(const char *text) {
    char *end = NULL;
    errno = 0;
    long value = strtol(text, &end, 10);
    if (errno != 0 || end == text || *end != '\0' || value <= STDERR_FILENO || value > 65535) {
        return -1;
    }
    return (int)value;
}

static int add_event(int queue, uintptr_t ident, int16_t filter, uint32_t fflags) {
    struct kevent change;
    EV_SET(&change, ident, filter, EV_ADD | EV_ENABLE, fflags, 0, NULL);
    return kevent(queue, &change, 1, NULL, 0, NULL);
}

/* Reap the target, retrying when a signal interrupts the wait. */
static int reap(pid_t child) {
    int status = 0;
    while (waitpid(child, &status, 0) < 0) {
        if (errno != EINTR) {
            return EXIT_SETUP;
        }
    }
    if (WIFEXITED(status)) {
        return WEXITSTATUS(status);
    }
    if (WIFSIGNALED(status)) {
        return 128 + WTERMSIG(status);
    }
    return EXIT_SETUP;
}

/* Kill the target's whole group, then reap the target. ESRCH only means the
 * group is already empty, so the result of killpg is deliberately ignored. */
static int finish(pid_t child, int cancelled) {
    (void)killpg(child, SIGKILL);
    int code = reap(child);
    return cancelled ? EXIT_CANCELLED : code;
}

static void run_target(char *const argv[]) {
    /* Undo the helper's own signal settings so the target starts clean. */
    for (size_t index = 0; index < STOP_SIGNAL_COUNT; index++) {
        signal(stop_signals[index], SIG_DFL);
    }
    if (setpgid(0, 0) == 0) {
        execve(argv[0], argv, environ);
    }
    _exit(errno == ENOENT || errno == ENOTDIR ? 127 : 126);
}

int main(int argc, char *argv[]) {
    if (argc < 3 || argv[2][0] != '/') {
        return EXIT_SETUP;
    }
    int control = parse_fd(argv[1]);
    if (control < 0 || fcntl(control, F_SETFD, FD_CLOEXEC) < 0) {
        return EXIT_SETUP;
    }
    if (getpgrp() != getpid() && setpgid(0, 0) < 0) {
        return EXIT_SETUP;
    }
    /* kqueue descriptors are not inherited across fork, so the target never
     * sees this queue. Close-on-exec is set as well for clarity. */
    int queue = kqueue();
    if (queue < 0 || fcntl(queue, F_SETFD, FD_CLOEXEC) < 0) {
        return EXIT_SETUP;
    }
    if (add_event(queue, (uintptr_t)control, EVFILT_READ, 0) < 0) {
        return EXIT_SETUP;
    }
    for (size_t index = 0; index < STOP_SIGNAL_COUNT; index++) {
        /* Ignored signals are still reported to kqueue. */
        signal(stop_signals[index], SIG_IGN);
        if (add_event(queue, (uintptr_t)stop_signals[index], EVFILT_SIGNAL, 0) < 0) {
            return EXIT_SETUP;
        }
    }

    pid_t child = fork();
    if (child < 0) {
        return EXIT_SETUP;
    }
    if (child == 0) {
        run_target(&argv[2]);
    }
    /* Also set the group from the parent so it exists before any kill below,
     * whichever process runs first. EACCES means the child already did it and
     * called execve, which is fine. */
    if (setpgid(child, child) < 0 && errno != EACCES) {
        (void)kill(child, SIGKILL);
        (void)reap(child);
        return EXIT_SETUP;
    }
    if (add_event(queue, (uintptr_t)child, EVFILT_PROC, NOTE_EXIT) < 0) {
        /* ESRCH: the target exited before it could be watched. */
        return finish(child, errno != ESRCH);
    }

    for (;;) {
        struct kevent event;
        int count = kevent(queue, NULL, 0, &event, 1, NULL);
        if (count < 0 && errno == EINTR) {
            continue;
        }
        if (count < 0) {
            return finish(child, 1);
        }
        if (count == 0) {
            continue;
        }
        if (event.filter == EVFILT_PROC) {
            return finish(child, 0);
        }
        /* Any readable state, data or end of file, on the control pipe and any
         * stop signal both mean cancel. The app never writes to the pipe. */
        return finish(child, 1);
    }
}
