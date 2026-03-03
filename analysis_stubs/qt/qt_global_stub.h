#pragma once

typedef double qreal;
typedef unsigned int quint32;
typedef unsigned short quint16;
typedef int int32_t;
typedef signed char int8_t;

class QObject {};
class QString {};
class QByteArray {
public:
    int size() const { return 0; }
    char at(int) const { return 0; }
    const char* data() const { return nullptr; }
};
template<typename T> class QList {};
template<typename T> class QVector {};
class QVariantList {};
class QMutex {};
class QThread {};
class QTimer {};
class QFile {};
class QDir {};