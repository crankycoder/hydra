
int open_mmap_file_rw(char* filename, size_t bytesize);
int open_mmap_file_ro(char* filepath);
char* map_file_rw(int fd, size_t filesize, int want_lock);
char* map_file_ro(int fd, size_t filesize, int want_lock);
void turn_bits_on(char *map, off_t index, char bitmask);
int flush_to_disk(int fd);
int close_file(int fd);
int unmap_file(char* map, size_t filesize);
void bulkload_file(char* buffer, char* filename);
