namespace MistLib
{
    /// <summary>Application callback codes shared by native and WASM in engine 0.7.1.</summary>
    public enum MistLibMessageType : uint
    {
        Raw = 0,
        Overlay = 1,
        PeerConnected = 2,
        PeerDisconnected = 3,
        Neighbors = 4,
        AoiEntered = 5,
        AoiLeft = 6,
        NodePositionUpdated = 7,
        AoiNodes = 8,
        AllConnectionsLost = 9,
        RoomJoined = 10,
        RoomJoinFailed = 11,
        RoomLeft = 12
    }
}
