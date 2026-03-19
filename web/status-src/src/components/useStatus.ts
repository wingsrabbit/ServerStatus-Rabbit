import { computed } from 'vue';
import { BoxItem, StatusItem } from '@/types';

interface Props {
  server: StatusItem | BoxItem;
}

export default (props: Props) => {
  const getStatus = computed((): boolean => {
    const s = props.server as BoxItem;
    if (s.online !== undefined) return s.online;
    return s.online4 || s.online6;
  });

  const getCpuStatus = computed((): number => (props.server as StatusItem).cpu === undefined ?
    100 : (props.server as StatusItem).cpu);

  const getRAMStatus = computed((): number => (props.server as StatusItem).memory_total === undefined ?
    100 : Math.round(((props.server as StatusItem).memory_used / (props.server as StatusItem).memory_total * 100)));

  const getHDDStatus = computed((): number => (props.server as StatusItem).hdd_total === undefined ?
    100 : Math.round(((props.server as StatusItem).hdd_used / (props.server as StatusItem).hdd_total * 100)));

  const getProcessBarStatus = computed(() => (data: number) => {
    if (data > 90) return 'error';
    else if (data > 70) return 'warning';
    else return 'success';
  });

  const tableRowByteConvert = computed(() => (data: number): string => {
    if (data < 1024) return data.toFixed(0) + 'B';
    else if (data < 1024 * 1024) return (data / 1024).toFixed(0) + 'K';
    else if (data < 1024 * 1024 * 1024) return (data / 1024 / 1024).toFixed(1) + 'M';
    else if (data < 1024 * 1024 * 1024 * 1024) return (data / 1024 / 1024 / 1024).toFixed(2) + 'G';
    else return (data / 1024 / 1024 / 1024 / 1024).toFixed(2) + 'T';
  });

  const expandRowByteConvert = computed(() => (data: number): string => {
    if (data < 1024) return data.toFixed(0) + ' B';
    else if (data < 1024 * 1024) return (data / 1024).toFixed(2) + ' KiB';
    else if (data < 1024 * 1024 * 1024) return (data / 1024 / 1024).toFixed(2) + ' MiB';
    else if (data < 1024 * 1024 * 1024 * 1024) return (data / 1024 / 1024 / 1024).toFixed(2) + ' GiB';
    else return (data / 1024 / 1024 / 1024 / 1024).toFixed(2) + ' TiB';
  });

  const formatUptime = computed((): string => {
    const s = props.server as StatusItem;
    const totalSeconds = parseInt(s.uptime) || 0;
    if (totalSeconds < 60) return `${totalSeconds}秒`;
    const days = Math.floor(totalSeconds / 86400);
    const hours = Math.floor((totalSeconds % 86400) / 3600);
    const minutes = Math.floor((totalSeconds % 3600) / 60);
    const seconds = totalSeconds % 60;
    if (days > 0) return `${days}天${hours}小时`;
    if (hours > 0) return `${hours}小时${minutes}分`;
    return `${minutes}分${seconds}秒`;
  });

  return {
    getStatus,
    getCpuStatus,
    getRAMStatus,
    getHDDStatus,
    getProcessBarStatus,
    tableRowByteConvert,
    expandRowByteConvert,
    formatUptime
  };
};
