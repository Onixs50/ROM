# contracts.py - Simple Smart Contracts for Martius Network

CONTRACTS = {
    "simple_token": {
        "name": "Simple Token",
        "code": """
pragma solidity ^0.8.19;

contract SimpleToken {
    string public name = "MartToken";
    string public symbol = "MART";
    uint8 public decimals = 18;
    uint256 public totalSupply = 1000000 * 10**18;
    address public owner;
    
    mapping(address => uint256) public balanceOf;
    mapping(address => mapping(address => uint256)) public allowance;
    
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Approval(address indexed owner, address indexed spender, uint256 value);
    
    constructor() {
        owner = msg.sender;
        balanceOf[msg.sender] = totalSupply;
        emit Transfer(address(0), msg.sender, totalSupply);
    }
    
    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "Insufficient balance");
        balanceOf[msg.sender] -= amount;
        balanceOf[to] += amount;
        emit Transfer(msg.sender, to, amount);
        return true;
    }
    
    function approve(address spender, uint256 amount) external returns (bool) {
        allowance[msg.sender][spender] = amount;
        emit Approval(msg.sender, spender, amount);
        return true;
    }
    
    function mint(address to, uint256 amount) external {
        require(msg.sender == owner, "Only owner");
        totalSupply += amount;
        balanceOf[to] += amount;
        emit Transfer(address(0), to, amount);
    }
}
""",
        "interactions": [
            {"name": "transfer", "args": ["random_address", "random_amount"]},
            {"name": "mint", "args": ["self_address", "1000000000000000000"]}
        ]
    },
    
    "simple_voting": {
        "name": "Simple Voting",
        "code": """
pragma solidity ^0.8.19;

contract SimpleVoting {
    address public owner;
    uint256 public yesVotes;
    uint256 public noVotes;
    mapping(address => bool) public hasVoted;
    
    event VoteCast(address voter, bool vote);
    
    constructor() {
        owner = msg.sender;
    }
    
    function vote(bool _vote) external {
        require(!hasVoted[msg.sender], "Already voted");
        hasVoted[msg.sender] = true;
        
        if (_vote) {
            yesVotes++;
        } else {
            noVotes++;
        }
        
        emit VoteCast(msg.sender, _vote);
    }
    
    function getResults() external view returns (uint256, uint256) {
        return (yesVotes, noVotes);
    }
}
""",
        "interactions": [
            {"name": "vote", "args": ["random_bool"]},
            {"name": "getResults", "args": []}
        ]
    },
    
    "simple_storage": {
        "name": "Simple Storage",
        "code": """
pragma solidity ^0.8.19;

contract SimpleStorage {
    uint256 public storedValue;
    address public owner;
    mapping(address => uint256) public userValues;
    
    event ValueStored(address user, uint256 value);
    
    constructor() {
        owner = msg.sender;
    }
    
    function store(uint256 _value) external {
        storedValue = _value;
        userValues[msg.sender] = _value;
        emit ValueStored(msg.sender, _value);
    }
    
    function retrieve() external view returns (uint256) {
        return storedValue;
    }
    
    function getUserValue(address _user) external view returns (uint256) {
        return userValues[_user];
    }
}
""",
        "interactions": [
            {"name": "store", "args": ["random_number"]},
            {"name": "retrieve", "args": []}
        ]
    },
    
    "simple_lottery": {
        "name": "Simple Lottery",
        "code": """
pragma solidity ^0.8.19;

contract SimpleLottery {
    address public owner;
    address[] public players;
    uint256 public ticketPrice = 0.001 ether;
    
    event PlayerEntered(address player);
    event WinnerSelected(address winner, uint256 amount);
    
    constructor() {
        owner = msg.sender;
    }
    
    function enter() external payable {
        require(msg.value >= ticketPrice, "Insufficient payment");
        players.push(msg.sender);
        emit PlayerEntered(msg.sender);
    }
    
    function pickWinner() external {
        require(msg.sender == owner, "Only owner");
        require(players.length > 0, "No players");
        
        uint256 index = uint256(keccak256(abi.encodePacked(block.timestamp, block.difficulty))) % players.length;
        address winner = players[index];
        uint256 prize = address(this).balance;
        
        payable(winner).transfer(prize);
        emit WinnerSelected(winner, prize);
        
        players = new address[](0);
    }
    
    function getPlayersCount() external view returns (uint256) {
        return players.length;
    }
}
""",
        "interactions": [
            {"name": "enter", "args": [], "value": "0.001"}
        ]
    },
    
    "simple_counter": {
        "name": "Simple Counter",
        "code": """
pragma solidity ^0.8.19;

contract SimpleCounter {
    uint256 public count;
    address public owner;
    mapping(address => uint256) public userCounts;
    
    event CountIncremented(address user, uint256 newCount);
    event CountReset();
    
    constructor() {
        owner = msg.sender;
        count = 0;
    }
    
    function increment() external {
        count++;
        userCounts[msg.sender]++;
        emit CountIncremented(msg.sender, count);
    }
    
    function reset() external {
        require(msg.sender == owner, "Only owner");
        count = 0;
        emit CountReset();
    }
    
    function getCount() external view returns (uint256) {
        return count;
    }
}
""",
        "interactions": [
            {"name": "increment", "args": []},
            {"name": "getCount", "args": []}
        ]
    }
}
