# Arduino комплектация для CubeSat 1U системы: Абсолютный код интеграции

## Обзор

Arduino комплектация для CubeSat 1U системы обеспечивает дополнительную гибкость и расширяемость системы. Абсолютность этой комплектации заключается в её способности интегрироваться с основной системой и обеспечивать дополнительные функции датчиков и управления.

## Список компонентов

### Основные компоненты

1. **Arduino Nano 33 IoT** (рекомендуется) или **Arduino Uno R3**
   - Микроконтроллер: ATmega328P (Uno) или SAMD21 (Nano 33 IoT)
   - Напряжение питания: 5V (Uno) или 3.3V (Nano 33 IoT)
   - Цифровые пины: 14 (Uno) или 22 (Nano 33 IoT)
   - Аналоговые пины: 8 (Uno) или 12 (Nano 33 IoT)

2. **Датчики для CubeSat**
   - **LIS3MDL** - 3-осевой магнитометр (цифровой датчик магнитного поля)
   - **BME280** - датчик температуры, давления и влажности
   - **TMP117** - прецизионный датчик температуры (цифровой)
   - **MCP3008** - 8-канальный 10-битный АЦП (SPI)
   - **SBM-20** - Geiger-Müller счетчик (радиация)

3. **Дополнительные модули**
   - **DS3231** - модуль часов реального времени (RTC)
   - **ADS1115** - 16-битный 4-канальный АЦП (I2C)
   - **GY-521** - MPU6050 (гироскоп и акселерометр)
   - **HC-05/HC-06** - Bluetooth модуль (для наземной настройки)

## Подключение датчиков

### I2C подключения (основные датчики)

```
Arduino Nano 33 IoT / Uno R3
├── VCC (3.3V или 5V) ──► LIS3MDL VCC
├── GND ──► LIS3MDL GND
├── SDA (A4 на Uno, D20 на Nano 33 IoT) ──► LIS3MDL SDA
├── SCL (A5 на Uno, D21 на Nano 33 IoT) ──► LIS3MDL SCL
├── VCC ──► BME280 VCC
├── GND ──► BME280 GND
├── SDA ──► BME280 SDA
├── SCL ──► BME280 SCL
├── VCC ──► TMP117 VCC
├── GND ──► TMP117 GND
├── SDA ──► TMP117 SDA
├── SCL ──► TMP117 SCL
└── VCC ──► DS3231 VCC
    ├── GND ──► DS3231 GND
    ├── SDA ──► DS3231 SDA
    └── SCL ──► DS3231 SCL
```

### SPI подключения

```
Arduino Nano 33 IoT / Uno R3
├── VCC ──► MCP3008 VDD, VREF
├── GND ──► MCP3008 AGND, DGND
├── D13 (SCK) ──► MCP3008 CLK
├── D12 (MISO) ──► MCP3008 DOUT
├── D11 (MOSI) ──► MCP3008 DIN
├── D10 ──► MCP3008 CS/SHDN
├── Channel 0 ──► SBM-20 Geiger Counter (через делитель напряжения)
├── Channel 1 ──► Внешний датчик 1
├── Channel 2 ──► Внешний датчик 2
└── Channel 3 ──► Внешний датчик 3
```

### Аналоговые подключения

```
Arduino Nano 33 IoT / Uno R3
├── A0 ──► SBM-20 Geiger Counter (через делитель напряжения)
├── A1 ──► Внешний датчик температуры
├── A2 ──► Внешний датчик напряжения
├── A3 ──► Внешний датчик тока
├── A6 ──► Внешний датчик (только на Nano)
└── A7 ──► Внешний датчик (только на Nano)
```

### Цифровые подключения

```
Arduino Nano 33 IoT / Uno R3
├── D2 ──► SBM-20 Geiger Counter (INT0 - для прерываний)
├── D3 ──► SBM-20 Geiger Counter (INT1 - резерв)
├── D4 ──► Светодиод состояния
├── D5 ──► Реле управления питанием
├── D6 ──► PWM для управления двигателем/приводом
├── D7 ──► Сигнальный выход
├── D8 ──► Сигнальный вход
├── D9 ──► PWM для управления сервоприводом
├── D10 ──► CS для MCP3008 (если используется SPI)
└── D13 ──► Встроенный светодиод (LED_BUILTIN)
```

## Подключение к основной системе

### UART/Serial подключения

```
Arduino Nano 33 IoT / Uno R3
├── TX (D1) ──► RX Raspberry Pi (GPIO 15)
├── RX (D0) ──► TX Raspberry Pi (GPIO 14)
└── GND ──► GND Raspberry Pi
```

### GPIO подключения

```
Arduino Nano 33 IoT / Uno R3
├── D17 (если используется) ──► GPIO 17 Raspberry Pi (Wake signal)
├── D27 (если используется) ──► GPIO 27 Raspberry Pi (Ready signal)
└── D22 (если используется) ──► GPIO 22 Raspberry Pi (Status LED)
```

## Программирование Arduino

### Установка библиотек

```cpp
// Основные библиотеки
#include <Wire.h>           // Для I2C коммуникации
#include <SPI.h>            // Для SPI коммуникации
#include <EEPROM.h>         // Для хранения данных

// Библиотеки для датчиков
#include <LIS3MDL.h>        // Для LIS3MDL магнитометра
#include <Adafruit_BME280.h> // Для BME280 датчика
#include <Adafruit_TMP117.h> // Для TMP117 датчика
#include <RTClib.h>         // Для DS3231 RTC
#include <Adafruit_ADS1X15.h> // Для ADS1115 АЦП
#include <I2Cdev.h>         // Для MPU6050
#include <MPU6050.h>        // Для MPU6050
```

### Пример кода для CubeSat Arduino

```cpp
/*
 * CubeSat Arduino Controller
 * Абсолютный код для CubeSat 1U системы
 */

#include <Wire.h>
#include <SPI.h>
#include <LIS3MDL.h>
#include <Adafruit_BME280.h>
#include <Adafruit_TMP117.h>
#include <RTClib.h>

// Инициализация датчиков
LIS3MDL lis;
Adafruit_BME280 bme;
Adafruit_TMP117 tmp117;
RTC_DS3231 rtc;

// Структура телеметрии
struct TelemetryData {
  uint8_t sync1 = 0xAA;
  uint8_t sync2 = 0x55;
  uint8_t packet_type = 0x01;
  uint16_t sequence_number = 0;
  uint32_t timestamp = 0;
  float mag_x = 0.0;
  float mag_y = 0.0;
  float mag_z = 0.0;
  uint16_t corrosion_raw = 0;
  uint32_t radiation_cps = 0;
  float temperature_bme = 0.0;
  float pressure = 0.0;
  float humidity = 0.0;
  float temperature_tmp = 0.0;
  uint16_t battery_voltage = 0;
  uint16_t checksum = 0;
};

TelemetryData current_telemetry;
volatile uint32_t radiation_pulse_count = 0;
uint32_t last_radiation_count = 0;

void setup() {
  Serial.begin(115200);
  
  // Инициализация I2C
  Wire.begin();
  
  // Инициализация датчиков
  if (!lis.begin_I2C()) {
    Serial.println("LIS3MDL not found!");
  }
  
  if (!bme.begin(0x76)) {  // Адрес BME280 может быть 0x76 или 0x77
    Serial.println("BME280 not found!");
  }
  
  if (!tmp117.begin()) {
    Serial.println("TMP117 not found!");
  }
  
  if (!rtc.begin()) {
    Serial.println("RTC not found!");
  }
  
  // Настройка прерываний для Geiger счетчика
  attachInterrupt(digitalPinToInterrupt(2), radiation_interrupt, RISING);
  
  // Настройка пинов
  pinMode(LED_BUILTIN, OUTPUT);
  digitalWrite(LED_BUILTIN, LOW);
  
  Serial.println("CubeSat Arduino Controller initialized");
}

void loop() {
  // Чтение данных с датчиков
  read_sensors();
  
  // Отправка телеметрии
  send_telemetry();
  
  // Задержка
  delay(1000); // 1 секунда
}

void read_sensors() {
  // Чтение магнитометра
  lis.read();
  current_telemetry.mag_x = lis.x_gauss * 0.0001; // Преобразование в Гауссы
  current_telemetry.mag_y = lis.y_gauss * 0.0001;
  current_telemetry.mag_z = lis.z_gauss * 0.0001;
  
  // Чтение BME280
  current_telemetry.temperature_bme = bme.readTemperature();
  current_telemetry.pressure = bme.readPressure() / 100.0; // гПа
  current_telemetry.humidity = bme.readHumidity();
  
  // Чтение TMP117
  current_telemetry.temperature_tmp = tmp117.readTempC();
  
  // Чтение RTC
  DateTime now = rtc.now();
  current_telemetry.timestamp = now.unixtime();
  
  // Чтение Geiger счетчика
  current_telemetry.radiation_cps = radiation_pulse_count - last_radiation_count;
  last_radiation_count = radiation_pulse_count;
  
  // Чтение батареи (через АЦП)
  int battery_raw = analogRead(A0);
  current_telemetry.battery_voltage = (battery_raw * 3.3 * 2) / 1024.0; // Напряжение в мВ
}

void send_telemetry() {
  // Увеличение номера последовательности
  current_telemetry.sequence_number++;
  
  // Вычисление контрольной суммы
  current_telemetry.checksum = calculate_checksum((uint8_t*)&current_telemetry, 
                                                 sizeof(TelemetryData) - 2);
  
  // Отправка телеметрии через Serial
  Serial.write((uint8_t*)&current_telemetry, sizeof(TelemetryData));
  
  // Мигание светодиодом
  digitalWrite(LED_BUILTIN, HIGH);
  delay(50);
  digitalWrite(LED_BUILTIN, LOW);
}

uint16_t calculate_checksum(void* data, uint16_t length) {
  uint16_t checksum = 0;
  uint8_t* bytes = (uint8_t*)data;
  
  for(uint16_t i = 0; i < length; i++) {
    checksum += bytes[i];
  }
  
  return checksum;
}

void radiation_interrupt() {
  radiation_pulse_count++;
}
```

## Конфигурация для CubeSat

### Параметры датчиков

| Датчик | Адрес | Параметры | Назначение |
|--------|-------|-----------|------------|
| LIS3MDL | 0x1C или 0x1E | ±4/8/12/16 gauss | Магнитное поле |
| BME280 | 0x76 или 0x77 | ±1Pa, 0.01°C, 0.008°C | Температура, давление, влажность |
| TMP117 | 0x48-0x4F | ±0.1°C | Прецизионная температура |
| DS3231 | 0x68 | ±3.5ppm | Время |

### Питание

- **Основное питание**: 3.3V или 5V от Raspberry Pi (через регулятор напряжения)
- **Потребление**: ~20-50mA в зависимости от активных датчиков
- **Регулятор напряжения**: AMS1117-3.3 или аналогичный для 5V→3.3V

### Безопасность подключения

1. **Делитель напряжения** для SBM-20 (Geiger счетчик):
   - R1 = 4.7MΩ, R2 = 470kΩ
   - Подключение к аналоговому пину

2. **Ограничитель тока** для светодиодов:
   - 220Ω резистор последовательно

3. **Фильтрация** для аналоговых сигналов:
   - RC фильтр (10kΩ + 100nF) для шумоподавления

## Тестирование системы

### Проверка подключения датчиков

```cpp
void test_sensors() {
  Serial.println("Testing sensors...");
  
  // Проверка LIS3MDL
  if (lis.begin_I2C()) {
    Serial.println("✓ LIS3MDL connected");
  } else {
    Serial.println("✗ LIS3MDL not found");
  }
  
  // Проверка BME280
  if (bme.begin(0x76)) {
    Serial.println("✓ BME280 connected");
  } else {
    Serial.println("✗ BME280 not found");
  }
  
  // Проверка TMP117
  if (tmp117.begin()) {
    Serial.println("✓ TMP117 connected");
  } else {
    Serial.println("✗ TMP117 not found");
  }
}
```

### Отладка и мониторинг

- **Serial Monitor**: 115200 baud для отладки
- **Светодиод индикации**: Мигает при отправке телеметрии
- **Прерывания**: Для точного подсчета импульсов Geiger счетчика

## Абсолютность интеграции

Абсолютность Arduino комплектации CubeSat 1U обеспечивается через:
- Совместимость с основной системой
- Надежное подключение датчиков
- Эффективное потребление энергии
- Точное измерение параметров
- Безопасное подключение компонентов

## Лицензия
MIT License