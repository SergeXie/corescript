class PlayerRank:
    def __init__(self, rankNo, roleId, roleIcon, roleName, roleJobName, rankValue, rankChange, rankValChange, userId, userName, serverId, openid, areaId, isHide):
        self.rankNo = rankNo
        self.roleId = roleId
        self.roleIcon = roleIcon
        self.roleName = roleName
        self.roleJobName = roleJobName
        self.rankValue = rankValue
        self.rankChange = rankChange
        self.rankValChange = rankValChange
        self.userId = userId
        self.userName = userName
        self.serverId = serverId
        self.openid = openid
        self.areaId = areaId
        self.isHide = isHide

    def __repr__(self):
        return f"PlayerRank(rankNo={self.rankNo}, roleId='{self.roleId}', roleName='{self.roleName}', rankValue='{self.rankValue}')" #简化打印输出信息。