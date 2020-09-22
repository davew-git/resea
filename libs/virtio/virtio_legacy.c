#include <endian.h>
#include <resea/ipc.h>
#include <resea/malloc.h>
#include <resea/printf.h>
#include <driver/irq.h>
#include <string.h>
#include <driver/io.h>
#include <virtio/virtio.h>
#include "virtio_legacy.h"

/// The maximum number of virtqueues.
#define NUM_VIRTQS_MAX 8

static task_t dm_server;
static struct virtio_virtq virtqs[NUM_VIRTQS_MAX];
static io_t bar0_io = NULL;

static uint8_t read_device_status(void) {
    return io_read8(bar0_io, REG_DEVICE_STATUS);
}

static void write_device_status(uint8_t value) {
    io_write8(bar0_io, REG_DEVICE_STATUS, value);
}

static uint64_t read_device_features(void) {
    return io_read32(bar0_io, REG_DEVICE_FEATS);
}


/// Returns the number of virtqueues in the device.
static uint16_t num_virtqueues(void) {
    NYI();
    return 0;
}

/// Reads the ISR status and de-assert an interrupt
/// ("4.1.4.5 ISR status capability").
static uint8_t read_isr_status(void) {
    return io_read8(bar0_io, REG_ISR_STATUS);
}

/// Returns the number of descriptors in total in the queue.
static uint16_t virtq_size(void) {
    return io_read16(bar0_io, REG_QUEUE_SIZE);
}

/// Returns the `index`-th virtqueue.
static struct virtio_virtq *virtq_get(unsigned index) {
    return &virtqs[index];
}

/// Notifies the device that the queue contains a descriptor it needs to process.
static void virtq_notify(struct virtio_virtq *vq) {
    return io_write16(bar0_io, REG_QUEUE_NOTIFY, vq->index);
}

/// Selects the current virtqueue in the common config.
static void virtq_select(unsigned index) {
    return io_write16(bar0_io, REG_QUEUE_SELECT, index);
}

/// Initializes a virtqueue.
static void virtq_init(unsigned index) {
    virtq_select(index);

    size_t num_descs = virtq_size();
    ASSERT(num_descs < 1024 && "too large queue size");

    /*
    offset_t queue_notify_off =
        notify_cap_off + VIRTIO_COMMON_CFG_READ16(queue_notify_off) * notify_off_multiplier;

    // Allocate the descriptor area.
    size_t descs_size = num_descs * sizeof(struct virtq_desc);
    dma_t descs_dma =
        dma_alloc(descs_size, DMA_ALLOC_TO_DEVICE | DMA_ALLOC_FROM_DEVICE);
    memset(dma_buf(descs_dma), 0, descs_size);

    // Allocate the driver area.
    dma_t driver_dma =
        dma_alloc(sizeof(struct virtq_event_suppress), DMA_ALLOC_TO_DEVICE);
    memset(dma_buf(driver_dma), 0, sizeof(struct virtq_event_suppress));

    // Allocate the device area.
    dma_t device_dma =
        dma_alloc(sizeof(struct virtq_event_suppress), DMA_ALLOC_TO_DEVICE);
    memset(dma_buf(device_dma), 0, sizeof(struct virtq_event_suppress));

    // Register physical addresses.
    set_desc_paddr(dma_daddr(descs_dma));
    set_driver_paddr(dma_daddr(driver_dma));
    set_device_paddr(dma_daddr(device_dma));
    VIRTIO_COMMON_CFG_WRITE16(queue_enable, 1);

    virtqs[index].index = index;
    virtqs[index].descs_dma = descs_dma;
    virtqs[index].descs = (struct virtq_desc *) dma_buf(descs_dma);
    virtqs[index].num_descs = num_descs;
    */
}

static void activate(void) {
    write_device_status(read_device_status() | VIRTIO_STATUS_DRIVER_OK);
}

/// Allocates a descriptor for the ouput to the device (e.g. TX virtqueue in
/// virtio-net).
static int virtq_alloc(struct virtio_virtq *vq, size_t len) {
    return 0;
}

/// Returns the next descriptor which is already used by the device. It returns
/// NULL if no descriptors are used. If the buffer is input from the device,
/// call `virtq_push_desc` once you've handled the input.
static struct virtq_desc *virtq_pop_desc(struct virtio_virtq *vq) {
    return NULL;
}

/// Makes the descriptor available for input from the device.
static void virtq_push_desc(struct virtio_virtq *vq, struct virtq_desc *desc) {
}

/// Allocates queue buffers. If `writable` is true, the buffers are initialized
/// as input ones from the device (e.g. RX virqueue in virtio-net).
static void virtq_allocate_buffers(struct virtio_virtq *vq, size_t buffer_size,
                                   bool writable) {
    dma_t dma = dma_alloc(buffer_size * vq->num_descs, DMA_ALLOC_FROM_DEVICE);
    vq->buffers_dma = dma;
    vq->buffers = dma_buf(dma);
    vq->buffer_size = buffer_size;

    uint16_t flags = writable ? (VIRTQ_DESC_F_AVAIL | VIRTQ_DESC_F_WRITE) : 0;
    for (int i = 0; i < vq->num_descs; i++) {
        vq->descs[i].id = into_le16(i);
        vq->descs[i].addr = into_le64(dma_daddr(dma) + (buffer_size * i));
        vq->descs[i].len = into_le32(buffer_size);
        vq->descs[i].flags = into_le16(flags);
    }
}

/// Checks and enables features. It aborts if any of the features is not supported.
static void negotiate_feature(uint64_t features) {
}

static uint32_t pci_config_read(handle_t device, unsigned offset, unsigned size) {
    struct message m;
    m.type = DM_PCI_READ_CONFIG_MSG;
    m.dm_pci_read_config.handle = device;
    m.dm_pci_read_config.offset = offset;
    m.dm_pci_read_config.size = size;
    ASSERT_OK(ipc_call(dm_server, &m));
    return m.dm_pci_read_config_reply.value;
}

static uint64_t read_device_config(offset_t offset, size_t size) {
    // TODO:
    return 0;
}

struct virtio_ops virtio_legacy_ops = {
    .read_device_features = read_device_features,
    .negotiate_feature = negotiate_feature,
    .read_device_config = read_device_config,
    .activate = activate,
    .read_isr_status = read_isr_status,
    .virtq_init = virtq_init,
    .virtq_get = virtq_get,
    .virtq_size = virtq_size,
    .virtq_allocate_buffers = virtq_allocate_buffers,
    .virtq_alloc = virtq_alloc,
    .virtq_pop_desc = virtq_pop_desc,
    .virtq_push_desc = virtq_push_desc,
    .virtq_notify = virtq_notify,
};

/// Looks for and initializes a virtio device with the given device type. It
/// sets the IRQ vector to `irq` on success.
error_t virtio_legacy_find_device(int device_type, struct virtio_ops **ops, uint8_t *irq) {
    // Search the PCI bus for a virtio device...
    dm_server = ipc_lookup("dm");
    struct message m;
    m.type = DM_ATTACH_PCI_DEVICE_MSG;
    m.dm_attach_pci_device.vendor_id = 0x1af4;
    m.dm_attach_pci_device.device_id = 0x1000;
    ASSERT_OK(ipc_call(dm_server, &m));
    handle_t pci_device = m.dm_attach_pci_device_reply.handle;

    uint32_t bar0 = pci_config_read(pci_device, 0x10, sizeof(uint8_t));
    ASSERT((bar0 & 1) == 1 && "BAR#0 should be io-mapped");

    bar0_io = io_alloc_port(bar0 & ~0b11, 32, IO_ALLOC_NORMAL);

    // Read the IRQ vector.
    *irq = pci_config_read(pci_device, 0x3c, sizeof(uint8_t));
    *ops = &virtio_legacy_ops;

    // "3.1.1 Driver Requirements: Device Initialization"
    write_device_status(0); // Reset the device.
    write_device_status(read_device_status() | VIRTIO_STATUS_ACK);
    write_device_status(read_device_status() | VIRTIO_STATUS_DRIVER);

    TRACE("found a virtio-legacy device");
    return OK;
}
