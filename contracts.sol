// SPDX-License-Identifier: MIT
pragma solidity ^0.8.24;

/*
All contracts are simple and gas-friendly, designed for testnet usage.
Each has at least one public interaction function you can call after deployment.
*/

contract Greeter {
    string public greeting;
    event Greeted(address indexed from, string newGreeting);

    constructor(string memory _greeting) {
        greeting = _greeting;
    }

    function setGreeting(string memory _greeting) external {
        greeting = _greeting;
        emit Greeted(msg.sender, _greeting);
    }
}

contract Counter {
    uint256 public count;
    event Incremented(address indexed from, uint256 newCount);

    function increment() external {
        unchecked { count++; }
        emit Incremented(msg.sender, count);
    }
}

contract SimpleStorage {
    uint256 public value;
    event ValueChanged(address indexed from, uint256 newValue);

    function set(uint256 _value) external {
        value = _value;
        emit ValueChanged(msg.sender, _value);
    }
}

contract Faucet {
    mapping(address => uint256) public lastDrip;
    uint256 public dripAmount = 10**15; // 0.001 units (for ERC20-like usage)
    event Dripped(address indexed to, uint256 amount);

    function setDripAmount(uint256 _amt) external {
        dripAmount = _amt;
    }

    function drip() external {
        // For demo purposes, just emit an event (no token transfer on-chain).
        // Interaction is still a tx that can be tracked.
        lastDrip[msg.sender] = block.timestamp;
        emit Dripped(msg.sender, dripAmount);
    }
}

contract YesNoVote {
    mapping(address => bool) public hasVoted;
    uint256 public yes;
    uint256 public no;
    event Voted(address indexed voter, bool choice);

    function vote(bool choice) external {
        require(!hasVoted[msg.sender], "already voted");
        hasVoted[msg.sender] = true;
        if (choice) { yes++; } else { no++; }
        emit Voted(msg.sender, choice);
    }
}

contract SimpleToken {
    string public name = "TestToken";
    string public symbol = "TT";
    uint8 public decimals = 18;
    uint256 public totalSupply;
    mapping(address => uint256) public balanceOf;
    event Transfer(address indexed from, address indexed to, uint256 value);
    event Mint(address indexed to, uint256 amount);

    function mint(uint256 amount) external {
        totalSupply += amount;
        balanceOf[msg.sender] += amount;
        emit Mint(msg.sender, amount);
        emit Transfer(address(0), msg.sender, amount);
    }

    function transfer(address to, uint256 amount) external returns (bool) {
        require(balanceOf[msg.sender] >= amount, "insufficient");
        unchecked {
            balanceOf[msg.sender] -= amount;
            balanceOf[to] += amount;
        }
        emit Transfer(msg.sender, to, amount);
        return true;
    }
}

contract SimpleNFT {
    string public name = "TestNFT";
    string public symbol = "TNFT";
    uint256 public totalMinted;
    mapping(uint256 => address) public ownerOf;
    mapping(address => uint256) public balanceOf;
    event Transfer(address indexed from, address indexed to, uint256 indexed tokenId);

    function mint() external {
        totalMinted++;
        uint256 tokenId = totalMinted;
        ownerOf[tokenId] = msg.sender;
        balanceOf[msg.sender] += 1;
        emit Transfer(address(0), msg.sender, tokenId);
    }
}

contract Registry {
    mapping(string => string) public records;
    event RecordSet(address indexed from, string key, string value);

    function setRecord(string calldata key, string calldata value) external {
        records[key] = value;
        emit RecordSet(msg.sender, key, value);
    }
}

contract TimeNote {
    struct Note { string data; uint256 at; }
    mapping(address => Note) public notes;
    event Noted(address indexed from, string data, uint256 at);

    function setNote(string calldata data) external {
        notes[msg.sender] = Note({data: data, at: block.timestamp});
        emit Noted(msg.sender, data, block.timestamp);
    }
}

contract Pinger {
    uint256 public pings;
    event Ping(address indexed from, uint256 count);

    function ping() external {
        unchecked { pings++; }
        emit Ping(msg.sender, pings);
    }
}
