import veins.modules.messages.BaseFrame1609_4;

namespace veins;

//
// Wireless messages (802.11p), all extend the WAVE short message frame.
// NOTE: OMNeT++ 6 msg6 maps `string` fields to opp_string storage with
// const char* getters/setters -- use C-string semantics in the C++ code.
//

packet RsuHello extends BaseFrame1609_4 {
    int rsuIndex;
}

packet KeyRequest extends BaseFrame1609_4 {
    string vehicleId;
}

packet KeyResponse extends BaseFrame1609_4 {
    string vehicleId;
    int rsuIndex;
}

packet AuthRequest extends BaseFrame1609_4 {
    string vehicleId;
    int round;
}

packet AuthBroadcast extends BaseFrame1609_4 {
    int round;
    int batchD;
    string targetVehicle; // empty = broadcast to the batch, else unicast (one-to-one mode)
}

packet AuthResponse extends BaseFrame1609_4 {
    string vehicleId;
    int round;
}

packet AuthAck extends BaseFrame1609_4 {
    int round;
    string ackedIds; // vehicle ids joined by ';'
}

packet CiphertextMsg extends BaseFrame1609_4 {
    string vehicleId;
    int n;
}

//
// Backend messages (RSU <-> AS), sent via sendDirect over the wired backhaul.
//

message BackAuthRequest {
    string vehicleId;
    int round;
    int rsuIndex;
}

message BackAuthResponse {
    string vehicleId;
    int round;
    int rsuIndex;
}

message BackBroadcast {
    int round;
    int kindCode; // 1 = delta, 2 = ack, 3 = per-vehicle delta (one-to-one mode)
    int batchD;
    string targetVehicle;
    string ackedIds;
}

message BackAggregate {
    int d;
    int n;
}

message ASTimer {
    int round;
    int what; // 0 = batch window expired, 1 = send delta, 2 = ack window, 3 = send per-vehicle delta, 4 = send per-vehicle ack
    string vehicleId;
    int rsuIndex;
}
