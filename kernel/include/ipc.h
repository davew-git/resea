#ifndef __IPC_H__
#define __IPC_H__

#include <types.h>

//
//  Syscall numbers and flags.
//
#define SYSCALL_IPC 0
#define SYSCALL_OPEN 1
#define SYSCALL_CLOSE 2
#define SYSCALL_LINK 3
#define SYSCALL_TRANSFER 4
#define SYSCALL_NOTIFY 5

#define IPC_SEND (1ull << 8)
#define IPC_RECV (1ull << 9)
#define IPC_REPLY (1ull << 10)
#define IPC_FROM_KERNEL (1ull << 11)
#define SYSCALL_TYPE(syscall_id) ((syscall_id) &0xff)

//
//  Message Header.
//
typedef uint32_t header_t;
#define MSG_INLINE_LEN_OFFSET 0
#define MSG_TYPE_OFFSET 16
#define MSG_PAGE_PAYLOAD (1ull << 11)
#define MSG_CHANNEL_PAYLOAD (1ull << 12)
#define INLINE_PAYLOAD_LEN(header) (((header) >> MSG_INLINE_LEN_OFFSET) & 0x7ff)
#define PAGE_PAYLOAD_ADDR(page) ((page) & 0xfffffffffffff000ull)
#define MSG_TYPE(header) (((header) >> MSG_TYPE_OFFSET) & 0xffff)
#define INTERFACE_ID(header) (MSG_TYPE(header) >> 8)
#define INLINE_PAYLOAD_LEN_MAX 2047
#define ERROR_TO_HEADER(error) ((uint32_t) (error) << MSG_TYPE_OFFSET)

// A bit mask to determine if a message satisfies one of fastpath
// prerequisites. This test checks if page/channel payloads are
// not contained in the message.
#define SYSCALL_FASTPATH_TEST(header) ((header) & 0x1800ull)

//
//  Notification.
//
typedef intmax_t notification_t;
enum notify_op {
    NOTIFY_OP_SET = 1,
    NOTIFY_OP_ADD = 2,
};

//
//  Page Payload.
//
typedef uintmax_t page_t;
#define PAGE_PAYLOAD(addr, exp, type) (addr | (exp << 0) | (type << 5))
#define PAGE_EXP(page) ((page) & 0x1f)
#define PAGE_TYPE(page) (((page) >> 5) & 0x3)
#define PAGE_TYPE_MOVE   1
#define PAGE_TYPE_SHARED 2

struct message {
    header_t header;
    cid_t from;
    uint32_t __padding1;
    cid_t channel;
    page_t page;
    uint64_t __padding2;
    uint8_t data[INLINE_PAYLOAD_LEN_MAX];
} PACKED;

struct process;
struct channel;
struct thread_info *get_thread_info(void);
struct channel *channel_create(struct process *process);
void channel_incref(struct channel *ch);
void channel_decref(struct channel *ch);
void channel_link(struct channel *ch1, struct channel *ch2);
void channel_transfer(struct channel *src, struct channel *dst);
error_t channel_notify(struct channel *ch, enum notify_op op, intmax_t arg0);
cid_t sys_open(void);
error_t sys_close(cid_t cid);
error_t sys_ipc(cid_t cid, uint32_t ops);
error_t sys_notify(cid_t ch, enum notify_op op, intmax_t arg0);
intmax_t syscall_handler(uintmax_t arg0, uintmax_t arg1, uintmax_t arg3,
                         uintmax_t syscall);
#endif
