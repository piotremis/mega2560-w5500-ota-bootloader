/* Project adaptation modified 2026-09-18: renamed variables and formatting. */
/* Cases from Arduino stk500boot.c; variable names and formatting adapted. GPL-2.0-or-later. */
case CMD_SIGN_ON:
out = 11;
packet[1] = STATUS_CMD_OK;
packet[2] = 8;
packet[3] = 'A';
packet[4] = 'V';
packet[5] = 'R';
packet[6] = 'I';
packet[7] = 'S';
packet[8] = 'P';
packet[9] = '_';
packet[10] = '2';
break;

case CMD_GET_PARAMETER: {
    unsigned char value;

    switch (packet[1]) {
    case PARAM_BUILD_NUMBER_LOW:
        value = CONFIG_PARAM_BUILD_NUMBER_LOW;
        break;
    case PARAM_BUILD_NUMBER_HIGH:
        value = CONFIG_PARAM_BUILD_NUMBER_HIGH;
        break;
    case PARAM_HW_VER:
        value = CONFIG_PARAM_HW_VER;
        break;
    case PARAM_SW_MAJOR:
        value = CONFIG_PARAM_SW_MAJOR;
        break;
    case PARAM_SW_MINOR:
        value = CONFIG_PARAM_SW_MINOR;
        break;
    default:
        value = 0;
        break;
    }
    out = 3;
    packet[1] = STATUS_CMD_OK;
    packet[2] = value;
} break;
